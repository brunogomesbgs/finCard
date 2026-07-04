import structlog
from app.infrastructure.persistence.models import OutboxEventDB
from app.infrastructure.messaging.tasks import publish_transaction_event

logger = structlog.get_logger()

class OutboxPublisher:
    async def publish_pending_events(self):
        pending_events = await OutboxEventDB.filter(status="PENDING").all()
        
        for event in pending_events:
            try:
                # Dispatch to Celery
                publish_transaction_event.delay(
                    event.id,
                    event.event_type,
                    event.payload
                )
                
                event.status = "PROCESSED"
                await event.save()
                logger.info("outbox_event_dispatched", event_id=event.id)
            except Exception as e:
                logger.error("outbox_dispatch_failed", event_id=event.id, error=str(e))
                event.status = "FAILED"
                await event.save()
