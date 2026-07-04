from celery import Celery
from kombu import Exchange, Queue
from app.infrastructure.persistence.config import settings

celery_app = Celery(
    "fincard",
    broker=settings.CELERY_BROKER_URL,
    include=["app.infrastructure.messaging.tasks"]
)

# DLQ Configuration
default_exchange = Exchange("default", type="direct")
dlq_exchange = Exchange("dlq", type="direct")

celery_app.conf.task_queues = (
    Queue(
        "default",
        default_exchange,
        routing_key="default",
        queue_arguments={
            "x-dead-letter-exchange": "dlq",
            "x-dead-letter-routing-key": "dlq",
        },
    ),
    Queue("dlq", dlq_exchange, routing_key="dlq"),
)
celery_app.conf.task_default_queue = "default"
celery_app.conf.task_default_exchange = "default"
celery_app.conf.task_default_routing_key = "default"

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "poll-outbox-every-10-seconds": {
            "task": "poll_outbox_events",
            "schedule": 10.0,
        },
    },
)
