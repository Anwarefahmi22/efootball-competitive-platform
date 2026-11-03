"""Database-backed throttling for the auth endpoints (audit 2026-11-01).

Before this module the login and register endpoints accepted unlimited
attempts, so passwords could be brute-forced and accounts mass-created
by bots. Vercel functions are stateless, so the counters live in the
``auth_throttle`` table (see the model and migration 016).

Policy
------
- Login, per (email, IP) pair: 5 failures inside 15 minutes -> that
  pair is locked 15 minutes. (AUD-19: the lock used to be per email
  alone, so anyone who knew a victim's email could keep the victim
  locked out from everywhere by failing 5 logins from their own IP.
  Pairing the lock to the attacker's IP removes that targeted-DoS:
  the victim's own IP is a different pair and stays unaffected. The
  accepted trade-off is that a distributed attacker gets 5 guesses
  per IP — bounded by the per-IP lock below and by password strength.)
- Login, per IP:    20 failures inside 15 minutes -> locked 15 minutes.
- Register, per IP: 10 attempts inside 60 minutes -> locked 60 minutes.
- A successful login clears the pair counter (the IP counter decays
  with its window; a shared IP should not stay punished forever, and
  20 failures is a high bar for a NAT full of honest players).

While locked, the endpoints answer 429 with a generic message; the
frontend localizes it through the i18n reverse dictionary.
"""
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, Request, status
from sqlalchemy import case, delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth_throttle import AuthThrottle

TOO_MANY = "Too many attempts. Try again later."

LOGIN_PAIR_LIMIT = 5
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
    """Count one hit in the sliding window; lock when the limit is hit.

    AUD-20: this is a single atomic INSERT ... ON CONFLICT DO UPDATE.
    The previous read-modify-write version lost counts whenever two
    requests raced the same key (both read count N, both wrote N+1);
    the upsert takes the row lock inside the statement, so concurrent
    hits serialize and every hit is counted. Window/lock semantics are
    unchanged: an expired window restarts the count at 1 and clears any
    stale lock; reaching the limit (re)locks for ``lock_for``.
    """
    now = _now()
    expired = AuthThrottle.window_started_at < now - window
    new_count = case((expired, 1), else_=AuthThrottle.fail_count + 1)
    lock_value = now + lock_for
    first_lock = lock_value if limit <= 1 else None
    stmt = pg_insert(AuthThrottle).values(
        key=key, fail_count=1, window_started_at=now, locked_until=first_lock
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=[AuthThrottle.key],
        set_={
            "fail_count": new_count,
            "window_started_at": case(
                (expired, now), else_=AuthThrottle.window_started_at
            ),
            "locked_until": case(
                (expired, first_lock),
                (new_count >= limit, lock_value),
                else_=AuthThrottle.locked_until,
            ),
        },
    )
    await db.execute(stmt)
    await db.commit()


async def clear_key(db: AsyncSession, key: str) -> None:
    await db.execute(delete(AuthThrottle).where(AuthThrottle.key == key))
    await db.commit()


async def enforce_quota(
    db: AsyncSession,
    key: str,
    *,
    limit: int,
    window: timedelta,
    lock_for: timedelta,
) -> None:
    """Per-user write quota (AUD-21), built on the throttle counters.

    Raises 429 when the caller is already at the limit for this window;
    otherwise records one use. Quotas guard abuse-sensitive creation
    endpoints (posts, tournaments, follows, comments) — competitive
    operations (match/challenge play) are deliberately never quota'd.
    """
    if await is_locked(db, key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=TOO_MANY
        )
    # The hit that reaches the limit still succeeds; the lock it sets
    # rejects the NEXT request. Exactly `limit` uses per window.
    await record_hit(db, key, limit=limit, window=window, lock_for=lock_for)
