"""Database-backed throttling for the auth endpoints (audit 2026-11-01).

Before this module the login and register endpoints accepted unlimited
attempts, so passwords could be brute-forced and accounts mass-created
by bots. Vercel functions are stateless, so the counters live in the
``auth_throttle`` table (see the model and migration 016).

Policy
------
- Login, per email: 5 failures inside 15 minutes -> locked 15 minutes.
- Login, per IP:    20 failures inside 15 minutes -> locked 15 minutes.
- Register, per IP: 10 attempts inside 60 minutes -> locked 60 minutes.
- A successful login clears the email counter (the IP counter decays
  with its window; a shared IP should not stay punished forever, and
  20 failures is a high bar for a NAT full of honest players).

While locked, the endpoints answer 429 with a generic message; the
frontend localizes it through the i18n reverse dictionary.
"""
from datetime import datetime, timedelta, timezone

from fastapi import Request
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth_throttle import AuthThrottle

TOO_MANY = "Too many attempts. Try again later."

LOGIN_EMAIL_LIMIT = 5
LOGIN_IP_LIMIT = 20
LOGIN_WINDOW = timedelta(minutes=15)
LOGIN_LOCK = timedelta(minutes=15)
REGISTER_IP_LIMIT = 10
REGISTER_WINDOW = timedelta(minutes=60)
REGISTER_LOCK = timedelta(minutes=60)


def _trust_proxy_headers() -> bool:
    """Whether X-Forwarded-For may be trusted in this deployment (AUD-11).

    On Vercel the platform itself sets X-Forwarded-For on every request
    (the runtime exposes the ``VERCEL`` env var), so the header is
    trustworthy there. Anywhere else — including the repo's long-running
    server track, which is directly reachable — a client can send any
    XFF it likes, so the header is ignored unless the operator explicitly
    declares a trusted proxy in front via ``TRUST_PROXY_HEADERS=1``.
    Evaluated per call, like ``core.media.media_backend``.
    """
    import os

    return os.environ.get("VERCEL") is not None or os.environ.get(
        "TRUST_PROXY_HEADERS"
    ) == "1"


def client_ip(request: Request) -> str:
    """Client IP for throttling: XFF only behind a trusted proxy."""
    if _trust_proxy_headers():
        forwarded = request.headers.get("x-forwarded-for", "")
        if forwarded:
            return forwarded.split(",")[0].strip()[:64]
    return (request.client.host if request.client else "unknown")[:64]


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def _get(db: AsyncSession, key: str) -> AuthThrottle | None:
    result = await db.execute(select(AuthThrottle).where(AuthThrottle.key == key))
    return result.scalar_one_or_none()


async def is_locked(db: AsyncSession, key: str) -> bool:
    row = await _get(db, key)
    return row is not None and row.locked_until is not None and row.locked_until > _now()


async def record_hit(
    db: AsyncSession,
    key: str,
    *,
    limit: int,
    window: timedelta,
    lock_for: timedelta,
) -> None:
    """Count one hit in the sliding window; lock when the limit is hit."""
    now = _now()
    row = await _get(db, key)
    if row is None:
        row = AuthThrottle(key=key, fail_count=0, window_started_at=now)
        db.add(row)
    if now - row.window_started_at > window:
        row.fail_count = 0
        row.window_started_at = now
        row.locked_until = None
    row.fail_count += 1
    if row.fail_count >= limit:
        row.locked_until = now + lock_for
    await db.commit()


async def clear_key(db: AsyncSession, key: str) -> None:
    await db.execute(delete(AuthThrottle).where(AuthThrottle.key == key))
    await db.commit()
