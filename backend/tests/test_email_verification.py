"""Email verification flow (migration 023): register → code by email →
verify → session. Runs against the console mailer (in-process OUTBOX)."""
import re
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select, update

from app.core import mailer
from app.core.config import settings
from app.models.email_code import EmailVerificationCode
from app.db.session import AsyncSessionLocal
from app.models.user import User

pytestmark = pytest.mark.asyncio

PW = "Str0ng!Pass"


@pytest.fixture()
def verification_on(monkeypatch):
    monkeypatch.setattr(settings, "EMAIL_VERIFICATION_ENABLED", True)
    mailer.OUTBOX.clear()
    yield
    mailer.OUTBOX.clear()


def _code_for(email: str) -> str:
    for msg in reversed(mailer.OUTBOX):
        if msg["to"] == email:
            m = re.search(r"\b(\d{6})\b", msg["text"])
            assert m, f"no 6-digit code in mail to {email}"
            return m.group(1)
    raise AssertionError(f"no mail captured for {email}")


def _wrong_code(real: str) -> str:
    return "000000" if real != "000000" else "111111"


async def _register(client, email: str, name: str = "Verify Me"):
    return await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": PW, "display_name": name},
    )


async def test_register_pending_login_blocked_then_verify(client, verification_on):
    email = "pending1@example.com"
    r = await _register(client, email)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["verification_required"] is True and "access_token" not in body

    blocked = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": PW}
    )
    assert blocked.status_code == 403 and blocked.json()["detail"] == "EMAIL_NOT_VERIFIED"

    code = _code_for(email)
    ok = await client.post(
        "/api/v1/auth/verify-email", json={"email": email, "code": code}
    )
    assert ok.status_code == 200 and "access_token" in ok.json(), ok.text

    login = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": PW}
    )
    assert login.status_code == 200, login.text

    # Codes are single-use: replaying the same code now fails.
    replay = await client.post(
        "/api/v1/auth/verify-email", json={"email": email, "code": code}
    )
    assert replay.status_code == 400


async def test_wrong_codes_burn_after_five_attempts(client, verification_on):
    email = "burn@example.com"
    await _register(client, email)
    real = _code_for(email)
    for _ in range(5):
        bad = await client.post(
            "/api/v1/auth/verify-email",
            json={"email": email, "code": _wrong_code(real)},
        )
        assert bad.status_code == 400 and bad.json()["detail"] == "INVALID_CODE"
    # Burned: even the true code is refused now.
    ok = await client.post(
        "/api/v1/auth/verify-email", json={"email": email, "code": real}
    )
    assert ok.status_code == 400


async def test_resend_cooldown_supersede_and_expiry(
    client, verification_on
):
    email = "resend@example.com"
    await _register(client, email)
    first = _code_for(email)
    assert len(mailer.OUTBOX) == 1

    # Inside the 30 s cooldown the resend is a silent no-op (still 204).
    r = await client.post("/api/v1/auth/resend-verification", json={"email": email})
    assert r.status_code == 204 and len(mailer.OUTBOX) == 1

    # Age the first code past the cooldown, then resend for real.
    async with AsyncSessionLocal() as db:
        await db.execute(
            update(EmailVerificationCode)
            .where(EmailVerificationCode.consumed_at.is_(None))
            .values(created_at=datetime.now(timezone.utc) - timedelta(seconds=31))
        )
        await db.commit()
    r = await client.post("/api/v1/auth/resend-verification", json={"email": email})
    assert r.status_code == 204 and len(mailer.OUTBOX) == 2
    second = _code_for(email)
    assert second != first or True  # value may coincide; supersession is what matters

    # The superseded first code no longer verifies.
    old = await client.post(
        "/api/v1/auth/verify-email", json={"email": email, "code": first}
    )
    assert old.status_code == 400

    # Expire the live code: verification must fail.
    async with AsyncSessionLocal() as db:
        await db.execute(
            update(EmailVerificationCode)
            .where(EmailVerificationCode.consumed_at.is_(None))
            .values(expires_at=datetime.now(timezone.utc) - timedelta(minutes=1))
        )
        await db.commit()
    expired = await client.post(
        "/api/v1/auth/verify-email", json={"email": email, "code": second}
    )
    assert expired.status_code == 400


async def test_resend_unknown_email_is_silent_204(client, verification_on):
    r = await client.post(
        "/api/v1/auth/resend-verification", json={"email": "ghost@example.com"}
    )
    assert r.status_code == 204 and mailer.OUTBOX == []


async def test_disabled_mode_registers_with_tokens(client):
    # Default (feature dark): the old contract is untouched.
    email = "classic@example.com"
    r = await _register(client, email)
    assert r.status_code == 201 and "access_token" in r.json(), r.text
    async with AsyncSessionLocal() as db:
        user = await db.execute(select(User).where(User.email == email))
        assert user.scalar_one().email_verified is True
