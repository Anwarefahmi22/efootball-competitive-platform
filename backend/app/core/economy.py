from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.economy import Transaction, TransactionType, Wallet


async def get_or_create_wallet(db: AsyncSession, user_id: UUID) -> Wallet:
    result = await db.execute(select(Wallet).where(Wallet.user_id == user_id))
    wallet = result.scalar_one_or_none()
    if wallet is None:
        wallet = Wallet(user_id=user_id, balance=0)
        db.add(wallet)
        await db.flush()
    return wallet


async def credit(
    db: AsyncSession, user_id: UUID, amount: int, tx_type: TransactionType, reference: str | None = None
) -> Wallet:
    if amount <= 0:
        raise ValueError("credit amount must be positive")
    wallet = await get_or_create_wallet(db, user_id)
    wallet.balance += amount
    db.add(
        Transaction(
            user_id=user_id,
            amount=amount,
            type=tx_type,
            balance_after=wallet.balance,
            reference=reference,
        )
    )
    return wallet


async def debit(
    db: AsyncSession, user_id: UUID, amount: int, tx_type: TransactionType, reference: str | None = None
) -> Wallet:
    if amount <= 0:
        raise ValueError("debit amount must be positive")
    wallet = await get_or_create_wallet(db, user_id)
    if wallet.balance < amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Insufficient wallet balance"
        )
    wallet.balance -= amount
    db.add(
        Transaction(
            user_id=user_id,
            amount=-amount,
            type=tx_type,
            balance_after=wallet.balance,
            reference=reference,
        )
    )
    return wallet
