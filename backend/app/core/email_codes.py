"""Verification-code lifecycle: issue, throttle, verify.

Rules (mirroring the OTP screen's visible behaviour):
- 6-digit code, 10-minute validity, single use.
- A new code invalidates every previous unconsumed code.
- Resend cooldown 30 s (the countdown the UI shows); at most 5 codes
  per user per hour.
- 5 wrong attempts burn the code.
Only the HMAC of the code is ever stored.
"""
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.email_code import EmailVerificationCode
from app.models.user import User

CODE_DIGITS = 6
CODE_TTL = timedelta(minutes=10)
MAX_ATTEMPTS = 5
RESEND_COOLDOWN = timedelta(seconds=30)
MAX_CODES_PER_HOUR = 5


def _hash_code(user_id, code: str) -> str:
    return hmac.new(
        settings.JWT_SECRET_KEY.encode(),
        f"{user_id}:{code}".encode(),
        hashlib.sha256,
    ).hexdigest()


class CooldownActive(Exception):
    def __init__(self, retry_after_seconds: int) -> None:
        self.retry_after_seconds = retry_after_seconds


class TooManyCodes(Exception):
    pass


async def issue_code(db: AsyncSession, user: User) -> str:
    """Create a fresh code for ``user`` and return its plaintext.

    Raises CooldownActive inside the 30 s resend window and
    TooManyCodes past the hourly cap.
    """
    now = datetime.now(timezone.utc)
    latest = await db.execute(
        select(EmailVerificationCode)
        .where(EmailVerificationCode.user_id == user.id)
        .order_by(EmailVerificationCode.created_at.desc())
        .limit(1)
    )
    last = latest.scalar_one_or_none()
    if last is not None:
        age = now - last.created_at
        if age < RESEND_COOLDOWN:
            raise CooldownActive(int((RESEND_COOLDOWN - age).total_seconds()) + 1)

    hour_ago = now - timedelta(hours=1)
    count = await db.execute(
        select(func.count())
        .select_from(EmailVerificationCode)
        .where(
            EmailVerificationCode.user_id == user.id,
            EmailVerificationCode.created_at >= hour_ago,
        )
    )
    if (count.scalar_one() or 0) >= MAX_CODES_PER_HOUR:
        raise TooManyCodes()

    # Supersede every still-open code.
    open_codes = await db.execute(
        select(EmailVerificationCode).where(
            EmailVerificationCode.user_id == user.id,
            EmailVerificationCode.consumed_at.is_(None),
        )
    )
    for stale in open_codes.scalars():
        stale.consumed_at = now

    code = f"{secrets.randbelow(10 ** CODE_DIGITS):0{CODE_DIGITS}d}"
    db.add(
        EmailVerificationCode(
            user_id=user.id,
            code_hash=_hash_code(user.id, code),
            expires_at=now + CODE_TTL,
        )
    )
    await db.flush()
    return code


async def verify_code(db: AsyncSession, user: User, code: str) -> bool:
    """Check ``code`` against the user's open code. On success the code
    is consumed and ``user.email_verified`` is set (caller commits)."""
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(EmailVerificationCode)
        .where(
            EmailVerificationCode.user_id == user.id,
            EmailVerificationCode.consumed_at.is_(None),
        )
        .order_by(EmailVerificationCode.created_at.desc())
        .limit(1)
    )
    row = result.scalar_one_or_none()
    if row is None or row.expires_at < now:
        return False
    if row.attempts >= MAX_ATTEMPTS:
        row.consumed_at = now
        return False
    if hmac.compare_digest(row.code_hash, _hash_code(user.id, code.strip())):
        row.consumed_at = now
        user.email_verified = True
        return True
    row.attempts += 1
    if row.attempts >= MAX_ATTEMPTS:
        row.consumed_at = now
    return False
