import uuid
from datetime import datetime
from typing import List, Optional
from app.infrastructure.persistence.models import EventStoreDB

class EventStore:
    @staticmethod
    async def append(
        aggregate_type: str,
        aggregate_id: uuid.UUID,
        event_type: str,
        payload: dict,
        actor_id: Optional[uuid.UUID] = None,
        actor_type: str = "USER",
        correlation_id: Optional[uuid.UUID] = None,
        sequence: Optional[int] = None,
        using_db=None
    ):
        if sequence is None:
            # Simple sequence management, in a real system we'd use a more robust way
            query = EventStoreDB.filter(
                aggregate_type=aggregate_type,
                aggregate_id=aggregate_id
            )
            if using_db:
                query = query.using_db(using_db)
            
            last_event = await query.order_by("-sequence").first()
            sequence = (last_event.sequence + 1) if last_event else 1

        event = await EventStoreDB.create(
            id=uuid.uuid4(),
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            event_type=event_type,
            payload=payload,
            payload_version=1,
            occurred_at=datetime.utcnow(),
            sequence=sequence,
            actor_id=actor_id,
            actor_type=actor_type,
            correlation_id=correlation_id,
            using_db=using_db
        )
        return event

    @staticmethod
    async def get_events(aggregate_id: uuid.UUID) -> List[EventStoreDB]:
        return await EventStoreDB.filter(aggregate_id=aggregate_id).order_by("sequence").all()
