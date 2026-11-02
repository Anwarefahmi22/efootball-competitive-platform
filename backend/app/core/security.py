import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any, Literal
from uuid import UUID, uuid4

import jwt
from jwt.exceptions import InvalidTokenError
from passlib.context import CryptContext

from app.core.config import settings

# AUD-24: PyJWT replaces the unmaintained python-jose. The wire format
# is unchanged (HS256, sub/type/exp claims), so tokens issued by the old
# library verify identically — access tokens survive the swap, and
# refresh tokens additionally gain a jti (AUD-10) that older tokens
# simply fail to present.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

TokenType = Literal["access", "refresh"]


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_token(
    subject: UUID, token_type: TokenType, extra_claims: dict[str, Any] | None = None
) -> str:
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
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(subject: UUID) -> tuple[str, UUID]:
    """Mint a refresh token with a unique jti (AUD-10).

    Returns (token, jti). The jti identifies the server-side
    refresh_sessions row that tracks this token's lifecycle.
    """
    jti = uuid4()
    return create_token(subject, "refresh", {"jti": str(jti)}), jti


def token_fingerprint(token: str) -> str:
    """SHA-256 of a token — stored server-side instead of the token."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _decode_payload(token: str, expected_type: TokenType) -> dict[str, Any]:
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
    except InvalidTokenError as exc:
        raise ValueError("Invalid token") from exc
    if payload.get("type") != expected_type:
        raise ValueError("Invalid token type")
    if not payload.get("sub"):
        raise ValueError("Invalid token subject")
    return payload


def decode_token(token: str, expected_type: TokenType) -> UUID:
    payload = _decode_payload(token, expected_type)
    return UUID(payload["sub"])


def decode_refresh_token(token: str) -> tuple[UUID, UUID]:
    """Decode a refresh token into (user_id, jti).

    Refresh tokens minted before AUD-10 carry no jti; they are rejected
    here, which is the documented one-time re-login at the AUD-10 deploy.
    """
    payload = _decode_payload(token, "refresh")
    jti = payload.get("jti")
    if not jti:
        raise ValueError("Refresh token has no session id")
    return UUID(payload["sub"]), UUID(jti)
