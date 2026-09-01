from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_user
from app.core.economy import credit, debit, get_or_create_wallet
from app.core.permissions import get_current_admin
from app.db.session import get_db
from app.models.economy import Transaction, TransactionType, WithdrawalRequest, WithdrawalStatus
from app.models.user import User
from app.schemas.economy import (
    DepositCreate,
    TransactionRead,
    WalletRead,
    WithdrawalCreate,
    WithdrawalRead,
)

router = APIRouter()


@router.get("/wallet/me", response_model=WalletRead)
async def my_wallet(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> WalletRead:
    wallet = await get_or_create_wallet(db, current_user.id)
    await db.commit()
    return WalletRead(user_id=wallet.user_id, balance=wallet.balance)


@router.get("/wallet/me/transactions", response_model=list[TransactionRead])
async def my_transactions(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[Transaction]:
    result = await db.execute(
        select(Transaction)
        .where(Transaction.user_id == current_user.id)
        .order_by(Transaction.created_at.desc())
    )
    return list(result.scalars().all())


@router.get("/wallet/{user_id}", response_model=WalletRead)
async def get_wallet(
    user_id: UUID, _admin: User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)
) -> WalletRead:
    wallet = await get_or_create_wallet(db, user_id)
    await db.commit()
    return WalletRead(user_id=wallet.user_id, balance=wallet.balance)


@router.post("/wallet/deposit", response_model=WalletRead, status_code=status.HTTP_201_CREATED)
async def manual_deposit(
    payload: DepositCreate,
    _admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> WalletRead:
    wallet = await credit(
        db, payload.user_id, payload.amount, TransactionType.DEPOSIT, payload.note
    )
    await db.commit()
    return WalletRead(user_id=wallet.user_id, balance=wallet.balance)


@router.post("/withdrawals", response_model=WithdrawalRead, status_code=status.HTTP_201_CREATED)
async def request_withdrawal(
    payload: WithdrawalCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WithdrawalRequest:
    await debit(
        db, current_user.id, payload.amount, TransactionType.WITHDRAWAL_REQUEST, "withdrawal request"
    )
    withdrawal = WithdrawalRequest(
        user_id=current_user.id, amount=payload.amount, status=WithdrawalStatus.PENDING
    )
    db.add(withdrawal)
    await db.commit()
    await db.refresh(withdrawal)
    return withdrawal


@router.get("/withdrawals", response_model=list[WithdrawalRead])
async def list_withdrawals(
    _admin: User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)
) -> list[WithdrawalRequest]:
    result = await db.execute(
        select(WithdrawalRequest).order_by(WithdrawalRequest.created_at.desc())
    )
    return list(result.scalars().all())


@router.post("/withdrawals/{withdrawal_id}/approve", response_model=WithdrawalRead)
async def approve_withdrawal(
    withdrawal_id: UUID,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> WithdrawalRequest:
    result = await db.execute(select(WithdrawalRequest).where(WithdrawalRequest.id == withdrawal_id))
    withdrawal = result.scalar_one_or_none()
    if withdrawal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Withdrawal not found")
    if withdrawal.status != WithdrawalStatus.PENDING:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Already resolved")

    withdrawal.status = WithdrawalStatus.APPROVED
    withdrawal.resolved_at = datetime.now(timezone.utc)
    withdrawal.resolved_by = admin.id
    await db.commit()
    await db.refresh(withdrawal)
    return withdrawal


@router.post("/withdrawals/{withdrawal_id}/reject", response_model=WithdrawalRead)
async def reject_withdrawal(
    withdrawal_id: UUID,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> WithdrawalRequest:
    result = await db.execute(select(WithdrawalRequest).where(WithdrawalRequest.id == withdrawal_id))
    withdrawal = result.scalar_one_or_none()
    if withdrawal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Withdrawal not found")
    if withdrawal.status != WithdrawalStatus.PENDING:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Already resolved")

    await credit(
        db, withdrawal.user_id, withdrawal.amount, TransactionType.WITHDRAWAL_REJECTED_REFUND,
        f"refund for rejected withdrawal {withdrawal.id}",
    )
    withdrawal.status = WithdrawalStatus.REJECTED
    withdrawal.resolved_at = datetime.now(timezone.utc)
    withdrawal.resolved_by = admin.id
    await db.commit()
    await db.refresh(withdrawal)
    return withdrawal
