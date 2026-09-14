from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_user
from app.core.security import decode_token
from app.db.session import get_db
from app.models.user import User

optional_bearer = HTTPBearer(auto_error=False)


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


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(optional_bearer),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """Like get_current_user, but resolves to None instead of raising.

    For endpoints that are public by design yet return one field that only the
    account owner or an admin should see. A missing, malformed or expired
    token is treated the same way: as "no identity", never as an error, so an
    anonymous visitor still gets the public part of the response.
    """
    if credentials is None:
        return None
    try:
        user_id = decode_token(credentials.credentials, "access")
    except ValueError:
        return None
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        return None
    return user
