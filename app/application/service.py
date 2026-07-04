import structlog
from app.domain.models import TransactionCreate, TransactionStatus
from app.infrastructure.persistence.models import TransactionDB, OutboxEventDB
from app.infrastructure.persistence.idempotency import IdempotencyService
from app.infrastructure.external.gateway import GatewayClient, GatewayError
from tortoise.transactions import in_transaction

logger = structlog.get_logger()

class TransactionService:
    def __init__(self):
        self.idempotency = IdempotencyService()
        self.gateway = GatewayClient()

    async def process_transaction(self, data: TransactionCreate):
        transaction_id_str = str(data.transaction_id)

        if await self.idempotency.is_processed(transaction_id_str):
            existing_tx = await TransactionDB.get(transaction_id=data.transaction_id)
            logger.info("transaction_already_processed", 
                        transaction_id=transaction_id_str,
                        original_amount=str(existing_tx.amount),
                        original_currency=existing_tx.currency)
            return existing_tx

        if not await self.idempotency.acquire_lock(transaction_id_str):
            logger.warn("transaction_locked", transaction_id=transaction_id_str)
            raise Exception("Transaction is being processed")

        try:
            async with in_transaction() as conn:
                tx_db, created = await TransactionDB.get_or_create(
                    transaction_id=data.transaction_id,
                    defaults={
                        "amount": data.amount,
                        "currency": data.currency,
                        "status": TransactionStatus.RECEBIDA
                    },
                    using_db=conn
                )
                
                if not created and tx_db.status == TransactionStatus.LIQUIDADA:
                    return tx_db

            try:
                await TransactionDB.filter(transaction_id=data.transaction_id).update(status=TransactionStatus.PROCESSANDO)
                gateway_response = await self.gateway.process_payment(
                    transaction_id_str, data.amount, data.currency
                )
                
                async with in_transaction() as conn:
                    tx_db.status = TransactionStatus.LIQUIDADA
                    await tx_db.save(using_db=conn)
                    
                    await OutboxEventDB.create(
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
                logger.error("gateway_failed", transaction_id=transaction_id_str, error=str(e))
                await TransactionDB.filter(transaction_id=data.transaction_id).update(status=TransactionStatus.FALHA)
                raise

        finally:
            await self.idempotency.release_lock(transaction_id_str)
