from celery import Celery
from app.infrastructure.persistence.config import settings

celery_app = Celery(
    "fincard",
    broker=settings.CELERY_BROKER_URL,
    include=["app.infrastructure.messaging.tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)
