from fastapi import APIRouter, HTTPException, Depends
from app.domain.models import TransactionCreate
from app.application.service import TransactionService
from app.infrastructure.persistence.outbox import OutboxPublisher
import structlog

router = APIRouter()
logger = structlog.get_logger()

@router.post("/transactions", status_code=201)
async def create_transaction(
    data: TransactionCreate,
    service: TransactionService = Depends(TransactionService)
):
    try:
        transaction = await service.process_transaction(data)

        publisher = OutboxPublisher()
        await publisher.publish_pending_events()
        
        return transaction
    except Exception as e:
        logger.error("api_transaction_failed", error=str(e), transaction_id=data.transaction_id)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def health_check():
    return {"status": "healthy"}
