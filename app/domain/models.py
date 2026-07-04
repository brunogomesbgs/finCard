from enum import Enum
from uuid import UUID
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class TransactionStatus(str, Enum):
    RECEBIDA = "RECEBIDA"
    PROCESSANDO = "PROCESSANDO"
    LIQUIDADA = "LIQUIDADA"
    FALHA = "FALHA"

class Transaction(BaseModel):
    transaction_id: UUID
    amount: float
    currency: str
    status: TransactionStatus
    created_at: datetime
    updated_at: Optional[datetime] = None

class TransactionCreate(BaseModel):
    transaction_id: UUID
    amount: float
    currency: str
