from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class TransactionType(str, Enum):
    DEPOSIT = "deposit"
    ENTRY_FEE = "entry_fee"
    PRIZE_PAYOUT = "prize_payout"
    WITHDRAWAL_REQUEST = "withdrawal_request"
    WITHDRAWAL_REJECTED_REFUND = "withdrawal_rejected_refund"
    ENTRY_FEE_REFUND = "entry_fee_refund"
    ADJUSTMENT = "adjustment"


class WithdrawalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class Wallet(Base):
    __tablename__ = "wallets"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    balance: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    amount: Mapped[int] = mapped_column(Integer, nullable=False)  # positive=credit, negative=debit
    type: Mapped[TransactionType] = mapped_column(String(32), nullable=False)
    balance_after: Mapped[int] = mapped_column(Integer, nullable=False)
    reference: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class WithdrawalRequest(Base):
    __tablename__ = "withdrawal_requests"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[WithdrawalStatus] = mapped_column(
        String(32), nullable=False, default=WithdrawalStatus.PENDING
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
