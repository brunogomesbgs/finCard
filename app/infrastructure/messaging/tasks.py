import structlog
import asyncio
from app.infrastructure.messaging.worker import celery_app

logger = structlog.get_logger()

@celery_app.task(name="publish_transaction_event")
def publish_transaction_event(event_id: int, event_type: str, payload: dict):
    logger.info("event_published", event_id=event_id, event_type=event_type, payload=payload)
    return True

@celery_app.task(name="poll_outbox_events")
def poll_outbox_events():
    from app.infrastructure.persistence.outbox import OutboxPublisher
    from tortoise import Tortoise
    from app.infrastructure.persistence.config import TORTOISE_CONFIG

    async def run_publisher():
        await Tortoise.init(config=TORTOISE_CONFIG)
        publisher = OutboxPublisher()
        await publisher.publish_pending_events()
        await Tortoise.close_connections()

    loop = asyncio.get_event_loop()
    loop.run_until_complete(run_publisher())
    return True
