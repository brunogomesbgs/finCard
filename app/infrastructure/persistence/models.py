from tortoise import fields, models
from app.domain.models import TransactionStatus, UserRole

class UserDB(models.Model):
    id = fields.UUIDField(primary_key=True)
    email = fields.CharField(max_length=255, unique=True, db_index=True)
    name = fields.CharField(max_length=255)
    password = fields.CharField(max_length=255)
    role = fields.CharEnumField(UserRole, default=UserRole.USER)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "users"

class TransactionDB(models.Model):
    id = fields.UUIDField(primary_key=True)
    transaction_id = fields.UUIDField(unique=True, db_index=True)
    user = fields.ForeignKeyField("models.UserDB", related_name="transactions", null=True)
    amount = fields.DecimalField(max_digits=20, decimal_places=2)
    currency = fields.CharField(max_length=3)
    status = fields.CharEnumField(TransactionStatus, default=TransactionStatus.RECEBIDA)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "transactions"

class EventStoreDB(models.Model):
    id = fields.UUIDField(primary_key=True)
    aggregate_type = fields.CharField(max_length=50)
    aggregate_id = fields.UUIDField()
    event_type = fields.CharField(max_length=100)
    payload = fields.JSONField()
    payload_version = fields.IntField() # smallint equivalent
    occurred_at = fields.DatetimeField()
    recorded_at = fields.DatetimeField(auto_now_add=True)
    sequence = fields.BigIntField()
    actor_id = fields.UUIDField(null=True)
    actor_type = fields.CharField(max_length=20)
    correlation_id = fields.UUIDField(null=True)
    encryption_key_id = fields.UUIDField(null=True)
    is_anonymized = fields.BooleanField(default=False)

    class Meta:
        table = "event_store"
        indexes = [
            ("aggregate_type", "aggregate_id", "sequence"),
            ("event_type", "occurred_at"),
            ("occurred_at",),
        ]
        # Partial indexes for actor_id and correlation_id need to be added manually or via migration
        # as Tortoise doesn't support partial indexes natively in the Meta.indexes

class OutboxEventDB(models.Model):
    id = fields.BigIntField(primary_key=True)
    event_type = fields.CharField(max_length=100)
    payload = fields.JSONField()
    status = fields.CharField(max_length=20, default="PENDING") # PENDING, PROCESSED, FAILED
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "outbox_events"
