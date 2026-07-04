from enum import Enum
from uuid import UUID
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class UserRole(str, Enum):
    USER = "USER"
    ADMIN = "ADMIN"

class TransactionStatus(str, Enum):
    RECEBIDA = "RECEBIDA"
    PROCESSANDO = "PROCESSANDO"
    LIQUIDADA = "LIQUIDADA"
    FALHA = "FALHA"

class UserCreate(BaseModel):
    email: str
    name: str
    password: str = Field(..., min_length=6)
    role: UserRole = UserRole.USER

class UserUpdatePassword(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=6)

class UserUpdate(BaseModel):
    email: Optional[str] = None
    name: Optional[str] = None

class UserResponse(BaseModel):
    id: UUID
    email: str
    name: str
    role: UserRole
    created_at: datetime

    class Config:
        from_attributes = True

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
