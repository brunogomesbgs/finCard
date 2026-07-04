from typing import Optional, List
import uuid
import structlog
from app.domain.models import UserCreate, UserUpdatePassword, UserRole, UserUpdate
from app.infrastructure.persistence.auth import get_password_hash, verify_password
from app.application.events.store import EventStore
from app.infrastructure.repositories.base import UserRepository
from tortoise.transactions import in_transaction

logger = structlog.get_logger()

class UserService:
    def __init__(self):
        self.repo = UserRepository()

    async def create_user(self, data: UserCreate, actor_id: Optional[uuid.UUID] = None):
        async with in_transaction() as conn:
            hashed_password = get_password_hash(data.password)
            user_id = uuid.uuid4()
            
            # Projection (Read Model)
            user = await self.repo.create(
                user_id=user_id,
                email=data.email,
                name=data.name,
                hashed_password=hashed_password,
                role=data.role,
                using_db=conn
            )
            
            # Event Sourcing
            await EventStore.append(
                aggregate_type="User",
                aggregate_id=user_id,
                event_type="UserCreated",
                payload={
                    "email": data.email,
                    "name": data.name,
                    "role": data.role
                },
                actor_id=actor_id or user_id,
                using_db=conn
            )
            
            logger.info("user_created", user_id=str(user_id), email=data.email)
            return user

    async def update_password(self, user_id: uuid.UUID, data: UserUpdatePassword):
        user = await self.repo.get_by_id(user_id)
        if not user or not verify_password(data.current_password, user.password):
            raise Exception("Invalid current password")
        
        async with in_transaction() as conn:
            hashed_new_password = get_password_hash(data.new_password)
            await self.repo.update_password(user_id, hashed_new_password, using_db=conn)
            
            await EventStore.append(
                aggregate_type="User",
                aggregate_id=user_id,
                event_type="UserPasswordUpdated",
                payload={},
                actor_id=user_id,
                using_db=conn
            )
            
            logger.info("user_password_updated", user_id=str(user_id))
            return True

    async def update_profile(self, user_id: uuid.UUID, data: UserUpdate):
        user = await self.repo.get_by_id(user_id)
        if not user:
            raise Exception("User not found")
        
        async with in_transaction() as conn:
            await self.repo.update_profile(
                user_id=user_id,
                email=data.email,
                name=data.name,
                using_db=conn
            )
            
            await EventStore.append(
                aggregate_type="User",
                aggregate_id=user_id,
                event_type="UserProfileUpdated",
                payload={
                    "email": data.email,
                    "name": data.name
                },
                actor_id=user_id,
                using_db=conn
            )
            
            logger.info("user_profile_updated", user_id=str(user_id))
            return await self.repo.get_by_id(user_id)

    async def list_users(self, role: UserRole):
        if role != UserRole.ADMIN:
            raise Exception("Unauthorized: Only admins can list users")
        return await self.repo.list_all()
