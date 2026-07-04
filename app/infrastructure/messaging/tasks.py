import structlog
from app.infrastructure.messaging.worker import celery_app

logger = structlog.get_logger()

@celery_app.task(name="publish_transaction_event")
def publish_transaction_event(event_id: int, event_type: str, payload: dict):
    logger.info("event_published", event_id=event_id, event_type=event_type, payload=payload)
    return True
