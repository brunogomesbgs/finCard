import uuid
from typing import Optional, List

from app.domain.models import TransactionStatus, UserRole
from app.infrastructure.persistence.models import TransactionDB, UserDB, OutboxEventDB


class TransactionRepository:
    async def get_by_transaction_id(self, transaction_id: uuid.UUID) -> Optional[TransactionDB]:
        return await TransactionDB.get_or_none(transaction_id=transaction_id)

    async def create_transaction(self, transaction_id: uuid.UUID, user_id: uuid.UUID, amount: float, currency: str, using_db=None) -> TransactionDB:
        user = await UserDB.get(id=user_id)
        return await TransactionDB.create(
            transaction_id=transaction_id,
            user=user,
            amount=amount,
            currency=currency,
            status=TransactionStatus.RECEBIDA,
            using_db=using_db
        )

    async def update_status(self, transaction_id: uuid.UUID, status: TransactionStatus, using_db=None):
        await TransactionDB.filter(transaction_id=transaction_id).using_db(using_db).update(status=status)

    async def list_by_user(self, user_id: uuid.UUID) -> List[TransactionDB]:
        return await TransactionDB.filter(user__id=user_id).order_by("-created_at").all()

    async def list_all(self) -> List[TransactionDB]:
        return await TransactionDB.all().order_by("-created_at").all()

class UserRepository:
    async def get_by_id(self, user_id: uuid.UUID) -> Optional[UserDB]:
        return await UserDB.get_or_none(id=user_id)

    async def get_by_email(self, email: str) -> Optional[UserDB]:
        return await UserDB.get_or_none(email=email)

    async def create(self, user_id: uuid.UUID, email: str, name: str, hashed_password: str, role: UserRole, using_db=None) -> UserDB:
        return await UserDB.create(
            id=user_id,
            email=email,
            name=name,
            password=hashed_password,
            role=role,
            using_db=using_db
        )

    async def update_password(self, user_id: uuid.UUID, hashed_password: str, using_db=None):
        await UserDB.filter(id=user_id).using_db(using_db).update(password=hashed_password)

    async def update_profile(self, user_id: uuid.UUID, email: Optional[str] = None, name: Optional[str] = None, using_db=None):
        update_data = {}
        if email:
            update_data["email"] = email
        if name:
            update_data["name"] = name
        
        if update_data:
            await UserDB.filter(id=user_id).using_db(using_db).update(**update_data)

    async def list_all(self) -> List[UserDB]:
        return await UserDB.all().order_by("-created_at").all()

    async def delete(self, user_id: uuid.UUID, using_db=None):
        await UserDB.filter(id=user_id).using_db(using_db).delete()

class OutboxRepository:
    async def create(self, event_type: str, payload: dict, using_db=None) -> OutboxEventDB:
        return await OutboxEventDB.create(
            event_type=event_type,
            payload=payload,
            status="PENDING",
            using_db=using_db
        )

    async def get_pending(self) -> List[OutboxEventDB]:
        return await OutboxEventDB.filter(status="PENDING").all()
