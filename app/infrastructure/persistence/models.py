from tortoise import fields, models
from app.domain.models import TransactionStatus

class TransactionDB(models.Model):
    id = fields.UUIDField(primary_key=True)
    transaction_id = fields.UUIDField(unique=True, db_index=True)
    amount = fields.DecimalField(max_digits=20, decimal_places=2)
    currency = fields.CharField(max_length=3)
    status = fields.CharEnumField(TransactionStatus, default=TransactionStatus.RECEBIDA)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "transactions"

class OutboxEventDB(models.Model):
    id = fields.BigIntField(primary_key=True)
    event_type = fields.CharField(max_length=100)
    payload = fields.JSONField()
    status = fields.CharField(max_length=20, default="PENDING") # PENDING, PROCESSED, FAILED
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "outbox_events"
