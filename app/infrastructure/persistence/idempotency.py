import redis.asyncio as redis
from app.infrastructure.persistence.config import settings

class IdempotencyService:
    def __init__(self):
        self.redis = redis.from_url(settings.REDIS_URL, decode_responses=True)

    async def is_processed(self, transaction_id: str) -> bool:
        exists = await self.redis.exists(f"idempotency:{transaction_id}")
        return exists > 0

    async def acquire_lock(self, transaction_id: str, timeout: int = 60) -> bool:
        # Use SET with NX (set if not exists) and EX (expire)
        return await self.redis.set(f"lock:{transaction_id}", "locked", nx=True, ex=timeout)

    async def release_lock(self, transaction_id: str):
        await self.redis.delete(f"lock:{transaction_id}")

    async def mark_as_processed(self, transaction_id: str, ttl: int = 86400):
        await self.redis.set(f"idempotency:{transaction_id}", "processed", ex=ttl)
