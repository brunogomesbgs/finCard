import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgres://fincard:fincard@localhost:5432/fincard")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", "amqp://guest:guest@localhost:5672//")
    GATEWAY_URL: str = os.getenv("GATEWAY_URL", "http://gateway:8080")

settings = Settings()

TORTOISE_CONFIG = {
    "connections": {"default": settings.DATABASE_URL},
    "apps": {
        "models": {
            "models": ["app.infrastructure.persistence.models", "aerich.models"],
            "default_connection": "default",
        }
    },
}
