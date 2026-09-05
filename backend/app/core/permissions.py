from fastapi import Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_user
from app.db.session import get_db
from app.models.user import User


async def get_current_admin(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Checks the is_admin column via raw SQL so we never have to touch the
    Phase 1 User model or auth module."""
    result = await db.execute(
        text("SELECT is_admin FROM users WHERE id = :uid"),
        {"uid": str(current_user.id)},
    )
    row = result.first()
    if row is None or not row[0]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
        )
    return current_user


async def is_admin(db: AsyncSession, user_id) -> bool:
    result = await db.execute(
        text("SELECT is_admin FROM users WHERE id = :uid"), {"uid": str(user_id)}
    )
    row = result.first()
    return bool(row and row[0])
