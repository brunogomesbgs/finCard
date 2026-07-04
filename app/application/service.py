import structlog
import uuid
from typing import Optional
from app.domain.models import TransactionCreate, TransactionStatus, UserRole
from app.infrastructure.persistence.idempotency import IdempotencyService
from app.infrastructure.external.gateway import GatewayClient, GatewayError
from app.application.events.store import EventStore
from app.infrastructure.repositories.base import TransactionRepository, OutboxRepository
from tortoise.transactions import in_transaction

logger = structlog.get_logger()

class TransactionService:
    def __init__(self):
        self.idempotency = IdempotencyService()
        self.gateway = GatewayClient()
        self.repo = TransactionRepository()
        self.outbox_repo = OutboxRepository()

    async def process_transaction(self, data: TransactionCreate, user_id: uuid.UUID):
        transaction_id_str = str(data.transaction_id)

        if await self.idempotency.is_processed(transaction_id_str):
            existing_tx = await self.repo.get_by_transaction_id(data.transaction_id)
            logger.info("transaction_already_processed", 
                        transaction_id=transaction_id_str,
                        original_amount=str(existing_tx.amount),
                        original_currency=existing_tx.currency)
            return existing_tx

        if not await self.idempotency.acquire_lock(transaction_id_str):
            logger.warn("transaction_locked", transaction_id=transaction_id_str)
            raise Exception("Transaction is being processed")

        try:
            # TRY phase
            async with in_transaction() as conn:
                existing_tx = await self.repo.get_by_transaction_id(data.transaction_id)
                if not existing_tx:
                    tx_db = await self.repo.create_transaction(
                        data.transaction_id, user_id, data.amount, data.currency, using_db=conn
                    )
                    await EventStore.append(
                        aggregate_type="Transaction",
                        aggregate_id=data.transaction_id,
                        event_type="TransactionReceived",
                        payload={
                            "user_id": str(user_id),
                            "amount": str(data.amount),
                            "currency": data.currency
                        },
                        actor_id=user_id,
                        using_db=conn
                    )
                else:
                    tx_db = existing_tx
                
                if tx_db.status == TransactionStatus.LIQUIDADA:
                    return tx_db

            try:
                # CONFIRM phase (Gateway call)
                await self.repo.update_status(data.transaction_id, TransactionStatus.PROCESSANDO)
                await EventStore.append(
                    aggregate_type="Transaction",
                    aggregate_id=data.transaction_id,
                    event_type="TransactionProcessingStarted",
                    payload={},
                    actor_id=user_id
                )

                gateway_response = await self.gateway.process_payment(
                    transaction_id_str, data.amount, data.currency
                )
                
                async with in_transaction() as conn:
                    tx_db.status = TransactionStatus.LIQUIDADA
                    await tx_db.save(using_db=conn)
                    
                    await EventStore.append(
                        aggregate_type="Transaction",
                        aggregate_id=data.transaction_id,
                        event_type="TransactionSettled",
                        payload={
                            "gateway_ref": gateway_response.get("id")
                        },
                        actor_id=user_id,
                        using_db=conn
                    )

                    await self.outbox_repo.create(
                        event_type="TransacaoLiquidadaEvent",
                        payload={
                            "transaction_id": transaction_id_str,
                            "amount": str(data.amount),
                            "currency": data.currency,
                            "gateway_ref": gateway_response.get("id")
                        },
                        using_db=conn
                    )
                
                await self.idempotency.mark_as_processed(transaction_id_str)
                logger.info("transaction_success", transaction_id=transaction_id_str)
                return tx_db

            except GatewayError as e:
                # CANCEL phase
                logger.error("gateway_failed", transaction_id=transaction_id_str, error=str(e))
                await self.repo.update_status(data.transaction_id, TransactionStatus.FALHA)
                await EventStore.append(
                    aggregate_type="Transaction",
                    aggregate_id=data.transaction_id,
                    event_type="TransactionFailed",
                    payload={"error": str(e)},
                    actor_id=user_id
                )
                raise
        finally:
            await self.idempotency.release_lock(transaction_id_str)

    async def list_user_transactions(self, user_id: uuid.UUID, role: UserRole):
        if role == UserRole.ADMIN:
            return await self.repo.list_all()
        else:
            return await self.repo.list_by_user(user_id)
