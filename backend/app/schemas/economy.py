from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.economy import TransactionType, WithdrawalStatus


class WalletRead(BaseModel):
    user_id: UUID
    balance: int


class TransactionRead(BaseModel):
    id: UUID
    amount: int
    type: TransactionType
    balance_after: int
    reference: str | None
    created_at: datetime


class DepositCreate(BaseModel):
    user_id: UUID
    amount: int = Field(gt=0)
    note: str | None = None


class WithdrawalCreate(BaseModel):
    amount: int = Field(gt=0)


class WithdrawalRead(BaseModel):
    id: UUID
    user_id: UUID
    amount: int
    status: WithdrawalStatus
    created_at: datetime
    resolved_at: datetime | None
