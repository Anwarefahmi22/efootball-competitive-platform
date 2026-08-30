from datetime import datetime, timedelta, timezone
from typing import Any, Literal
from uuid import UUID

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

TokenType = Literal["access", "refresh"]


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_token(subject: UUID, token_type: TokenType) -> str:
    if token_type == "access":
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )
    payload: dict[str, Any] = {
        "sub": str(subject),
        "type": token_type,
        "exp": expire,
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str, expected_type: TokenType) -> UUID:
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
    except JWTError as exc:
        raise ValueError("Invalid token") from exc
    if payload.get("type") != expected_type:
        raise ValueError("Invalid token type")
    sub = payload.get("sub")
    if not sub:
        raise ValueError("Invalid token subject")
    return UUID(sub)
