import pytest
from uuid import uuid4
from decimal import Decimal
from unittest.mock import AsyncMock, patch
from app.domain.models import TransactionCreate, TransactionStatus
from app.application.service import TransactionService
from app.infrastructure.persistence.models import TransactionDB
from tortoise import Tortoise

@pytest.fixture(autouse=True)
async def db():
    await Tortoise.init(
        db_url="sqlite://:memory:",
        modules={"models": ["app.infrastructure.persistence.models"]}
    )
    await Tortoise.generate_schemas()
    try:
        yield
    finally:
        await Tortoise.close_connections()

@pytest.mark.asyncio
async def test_process_transaction_success():
    with patch("app.application.service.IdempotencyService") as mock_idem, \
         patch("app.application.service.GatewayClient") as mock_gateway, \
         patch("app.application.service.OutboxEventDB.create") as mock_outbox:
        
        mock_idem.return_value.is_processed = AsyncMock(return_value=False)
        mock_idem.return_value.acquire_lock = AsyncMock(return_value=True)
        mock_idem.return_value.release_lock = AsyncMock()
        mock_idem.return_value.mark_as_processed = AsyncMock()
        mock_gateway.return_value.process_payment = AsyncMock(return_value={"id": "gw_123"})
        
        service = TransactionService()
        tx_id = uuid4()
        data = TransactionCreate(transaction_id=tx_id, amount=100.0, currency="BRL")
        
        result = await service.process_transaction(data)
        
        assert result.transaction_id == tx_id
        assert result.status == TransactionStatus.LIQUIDADA

        db_tx = await TransactionDB.get(transaction_id=tx_id)
        assert db_tx.status == TransactionStatus.LIQUIDADA
        assert db_tx.amount == Decimal("100.00")

@pytest.mark.asyncio
async def test_process_transaction_idempotency():
    with patch("app.application.service.IdempotencyService") as mock_idem:
        mock_idem.return_value.is_processed = AsyncMock(return_value=True)

        # uuid version 4, in a future update to v7 with postgres 17
        tx_id = uuid4()
        await TransactionDB.create(
            transaction_id=tx_id,
            amount=100.0,
            currency="BRL",
            status=TransactionStatus.LIQUIDADA
        )
        
        service = TransactionService()
        data = TransactionCreate(transaction_id=tx_id, amount=100.0, currency="BRL")
        
        result = await service.process_transaction(data)
        
        assert result.transaction_id == tx_id
        assert result.status == TransactionStatus.LIQUIDADA
