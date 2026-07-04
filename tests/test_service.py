import pytest
from uuid import uuid4
from decimal import Decimal
from unittest.mock import AsyncMock, patch
from app.domain.models import TransactionCreate, TransactionStatus, UserCreate, UserRole, UserUpdate
from app.application.service import TransactionService
from app.application.user_service import UserService
from app.infrastructure.persistence.models import TransactionDB, UserDB, EventStoreDB
from tortoise import Tortoise

@pytest.fixture(autouse=True)
async def db():
    await Tortoise.init(
        db_url="sqlite://:memory:",
        modules={"models": ["app.infrastructure.persistence.models", "aerich.models"]}
    )
    await Tortoise.generate_schemas()
    try:
        yield
    finally:
        await Tortoise.close_connections()

@pytest.mark.asyncio
async def test_process_transaction_success():
    user_service = UserService()
    user = await user_service.create_user(UserCreate(email="test@test.com", name="Test", password="password", role=UserRole.USER))

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
        
        result = await service.process_transaction(data, user.id)
        
        assert result.transaction_id == tx_id
        assert result.status == TransactionStatus.LIQUIDADA

        db_tx = await TransactionDB.get(transaction_id=tx_id)
        assert db_tx.status == TransactionStatus.LIQUIDADA
        assert db_tx.amount == Decimal("100.00")
        assert db_tx.user_id == user.id

        # Verify Event Store
        events = await EventStoreDB.filter(aggregate_id=tx_id).order_by("sequence").all()
        assert len(events) >= 3 # Received, Processing, Settled
        assert events[0].event_type == "TransactionReceived"
        assert events[-1].event_type == "TransactionSettled"

@pytest.mark.asyncio
async def test_process_transaction_idempotency():
    user_service = UserService()
    user = await user_service.create_user(UserCreate(email="test@test.com", name="Test", password="password", role=UserRole.USER))

    with patch("app.application.service.IdempotencyService") as mock_idem:
        mock_idem.return_value.is_processed = AsyncMock(return_value=True)

        tx_id = uuid4()
        await TransactionDB.create(
            transaction_id=tx_id,
            user_id=user.id,
            amount=100.0,
            currency="BRL",
            status=TransactionStatus.LIQUIDADA
        )
        
        service = TransactionService()
        data = TransactionCreate(transaction_id=tx_id, amount=100.0, currency="BRL")
        
        result = await service.process_transaction(data, user.id)
        
        assert result.transaction_id == tx_id
        assert result.status == TransactionStatus.LIQUIDADA

@pytest.mark.asyncio
async def test_list_transactions_role_access():
    user_service = UserService()
    user1 = await user_service.create_user(UserCreate(email="user1@test.com", name="U1", password="password", role=UserRole.USER))
    user2 = await user_service.create_user(UserCreate(email="user2@test.com", name="U2", password="password", role=UserRole.USER))
    admin = await user_service.create_user(UserCreate(email="admin@test.com", name="Admin", password="password", role=UserRole.ADMIN))

    await TransactionDB.create(transaction_id=uuid4(), user_id=user1.id, amount=10.0, currency="BRL")
    await TransactionDB.create(transaction_id=uuid4(), user_id=user2.id, amount=20.0, currency="BRL")

    service = TransactionService()
    
    # User 1 should only see their own
    txs1 = await service.list_user_transactions(user1.id, user1.role)
    assert len(txs1) == 1
    assert txs1[0].user_id == user1.id

    # Admin should see all
    txs_admin = await service.list_user_transactions(admin.id, admin.role)
    assert len(txs_admin) == 2

@pytest.mark.asyncio
async def test_update_user_profile():
    user_service = UserService()
    user = await user_service.create_user(UserCreate(
        email="old@test.com", 
        name="Old Name", 
        password="password", 
        role=UserRole.USER
    ))

    update_data = UserUpdate(name="New Name", email="new@test.com")
    updated_user = await user_service.update_profile(user.id, update_data)

    assert updated_user.name == "New Name"
    assert updated_user.email == "new@test.com"

    # Verify Database
    db_user = await UserDB.get(id=user.id)
    assert db_user.name == "New Name"
    assert db_user.email == "new@test.com"

    # Verify Event Store
    events = await EventStoreDB.filter(aggregate_id=user.id, event_type="UserProfileUpdated").all()
    assert len(events) == 1
    assert events[0].payload["name"] == "New Name"
    assert events[0].payload["email"] == "new@test.com"

@pytest.mark.asyncio
async def test_admin_list_users():
    user_service = UserService()
    # Create an admin
    admin = await user_service.create_user(UserCreate(
        email="admin_list@test.com",
        name="Admin User",
        password="password",
        role=UserRole.ADMIN
    ))
    # Create a regular user
    await user_service.create_user(UserCreate(
        email="user_list@test.com",
        name="Regular User",
        password="password",
        role=UserRole.USER
    ))

    # Admin should be able to list users
    users = await user_service.list_users(UserRole.ADMIN)
    assert len(users) >= 2
    emails = [u.email for u in users]
    assert "admin_list@test.com" in emails
    assert "user_list@test.com" in emails

    # Regular user should NOT be able to list users
    with pytest.raises(Exception, match="Unauthorized: Only admins can list users"):
        await user_service.list_users(UserRole.USER)
