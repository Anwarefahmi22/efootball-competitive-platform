"""Stage 4 acceptance tests: AUD-10, AUD-19, AUD-21, AUD-22, AUD-24."""
import os

import jwt as pyjwt
import pytest

pytestmark = pytest.mark.asyncio

PASSWORD = "TestPass!2026"


@pytest.fixture
def two_ips(monkeypatch):
    """AUD-11 lets tests simulate source IPs via X-Forwarded-For."""
    monkeypatch.setenv("TRUST_PROXY_HEADERS", "1")
    yield


async def _login(client, email, password=PASSWORD, ip=None):
    headers = {"X-Forwarded-For": ip} if ip else {}
    return await client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}, headers=headers
    )


# ---------------------------------------------------------------- AUD-24

async def test_password_over_bcrypt_byte_limit_is_rejected(client):
    # 40 x 2-byte chars = 80 bytes: passes the 72-CHARACTER cap that
    # used to be the only check, must fail the 72-BYTE policy.
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "bytes@arena.dev", "password": "é" * 40, "display_name": "Bytes"},
    )
    assert resp.status_code == 422
    # A multibyte password within the byte budget registers fine.
    ok = await client.post(
        "/api/v1/auth/register",
        json={"email": "bytes2@arena.dev", "password": "é" * 30 + "abcd", "display_name": "Bytes"},
    )
    assert ok.status_code == 201, ok.text


async def test_expired_and_wrong_type_tokens_rejected(client, register_user):
    uid, headers = await register_user()
    access = headers["Authorization"].split()[1]
    # Access token presented as a refresh token.
    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": access})
    assert resp.status_code == 401
    # Expired token (signed with the suite's test secret).
    expired = pyjwt.encode(
        {"sub": str(uid), "type": "access", "exp": 1},
        os.environ["JWT_SECRET_KEY"],
        algorithm="HS256",
    )
    resp = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {expired}"}
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------- AUD-10

async def test_refresh_rotation_and_old_token_rejection(client):
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "rotate@arena.dev", "password": PASSWORD, "display_name": "Rot"},
    )
    assert reg.status_code == 201, reg.text
    r1 = reg.json()["refresh_token"]
    rotated = await client.post("/api/v1/auth/refresh", json={"refresh_token": r1})
    assert rotated.status_code == 200, rotated.text
    r2 = rotated.json()["refresh_token"]
    assert r2 and r2 != r1
    # The new token works.
    again = await client.post("/api/v1/auth/refresh", json={"refresh_token": r2})
    assert again.status_code == 200
    # Replaying the retired token is rejected.
    replay = await client.post("/api/v1/auth/refresh", json={"refresh_token": r1})
    assert replay.status_code == 401


async def test_refresh_reuse_revokes_family_after_grace(client, register_user):
    from sqlalchemy import text

    from app.db.session import AsyncSessionLocal

    uid, headers = await register_user()
    # Build a session chain directly through the API: login is needed
    # for a refresh token; register_user returns only an access token,
    # so log in with the account it created via a password reset-free
    # path: re-register is impossible — instead use a fresh account
    # created here through the API.
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "family@arena.dev", "password": PASSWORD, "display_name": "Fam"},
    )
    assert reg.status_code == 201, reg.text
    r1 = reg.json()["refresh_token"]
    step = await client.post("/api/v1/auth/refresh", json={"refresh_token": r1})
    r2 = step.json()["refresh_token"]
    # Age the rotation beyond the 30s grace window, then replay r1:
    # the whole family must die, including the currently-valid r2.
    async with AsyncSessionLocal() as db:
        await db.execute(
            text("UPDATE refresh_sessions SET rotated_at = rotated_at - interval '120 seconds' WHERE rotated_at IS NOT NULL")
        )
        await db.commit()
    replay = await client.post("/api/v1/auth/refresh", json={"refresh_token": r1})
    assert replay.status_code == 401
    killed = await client.post("/api/v1/auth/refresh", json={"refresh_token": r2})
    assert killed.status_code == 401


async def test_logout_revokes_session(client):
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "logout@arena.dev", "password": PASSWORD, "display_name": "Out"},
    )
    r1 = reg.json()["refresh_token"]
    out = await client.post("/api/v1/auth/logout", json={"refresh_token": r1})
    assert out.status_code == 204
    after = await client.post("/api/v1/auth/refresh", json={"refresh_token": r1})
    assert after.status_code == 401
    # Logout is idempotent.
    again = await client.post("/api/v1/auth/logout", json={"refresh_token": r1})
    assert again.status_code == 204
    garbage = await client.post("/api/v1/auth/logout", json={"refresh_token": "not-a-token"})
    assert garbage.status_code == 204


async def test_legacy_refresh_token_without_jti_rejected(client, register_user):
    uid, _ = await register_user()
    legacy = pyjwt.encode(
        {"sub": str(uid), "type": "refresh", "exp": 4102444800},
        os.environ["JWT_SECRET_KEY"],
        algorithm="HS256",
    )
    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": legacy})
    assert resp.status_code == 401


# ---------------------------------------------------------------- AUD-19

async def test_lockout_is_scoped_to_attacker_ip(client, two_ips):
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "victim@arena.dev", "password": PASSWORD, "display_name": "Vic"},
        headers={"X-Forwarded-For": "9.9.9.9"},
    )
    assert reg.status_code == 201
    # Attacker at 1.1.1.1 burns the pair budget.
    for _ in range(5):
        bad = await _login(client, "victim@arena.dev", "WrongPass!1", ip="1.1.1.1")
        assert bad.status_code == 401
    sixth = await _login(client, "victim@arena.dev", "WrongPass!1", ip="1.1.1.1")
    assert sixth.status_code == 429
    # Even the correct password from the ATTACKER's IP is locked...
    locked = await _login(client, "victim@arena.dev", ip="1.1.1.1")
    assert locked.status_code == 429
    # ...but the victim, from their own IP, logs in immediately.
    victim = await _login(client, "victim@arena.dev", ip="2.2.2.2")
    assert victim.status_code == 200, victim.text


# ---------------------------------------------------------------- AUD-21

async def test_post_quota_and_per_user_isolation(client, register_user):
    _, h1 = await register_user()
    _, h2 = await register_user()
    for i in range(20):
        resp = await client.post("/api/v1/posts", headers=h1, data={"content": f"post {i}"})
        assert resp.status_code == 201, resp.text
    over = await client.post("/api/v1/posts", headers=h1, data={"content": "one too many"})
    assert over.status_code == 429
    other = await client.post("/api/v1/posts", headers=h2, data={"content": "still fine"})
    assert other.status_code == 201


async def test_tournament_quota(client, register_user):
    _, h = await register_user()
    for i in range(10):
        resp = await client.post(
            "/api/v1/tournaments", headers=h, json={"name": f"T{i}", "max_participants": 4}
        )
        assert resp.status_code == 201, resp.text
    over = await client.post(
        "/api/v1/tournaments", headers=h, json={"name": "T11", "max_participants": 4}
    )
    assert over.status_code == 429


# ---------------------------------------------------------------- AUD-22

async def test_security_headers_present(client):
    resp = await client.get("/health")
    assert resp.headers["X-Content-Type-Options"] == "nosniff"
    assert resp.headers["X-Frame-Options"] == "DENY"
    assert resp.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert "default-src 'self'" in resp.headers["Content-Security-Policy"]
    assert resp.headers["Strict-Transport-Security"].startswith("max-age=")
