"""AUD-01: auth API behaviour + AUD-17/AUD-18 regression coverage."""
import pytest

pytestmark = pytest.mark.asyncio


async def test_register_login_me_refresh_flow(client):
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "flow@arena.dev", "password": "TestPass!2026", "display_name": "Flow"},
    )
    assert reg.status_code == 201
    tokens = reg.json()
    assert tokens["access_token"] and tokens["refresh_token"]

    login = await client.post(
        "/api/v1/auth/login", json={"email": "flow@arena.dev", "password": "TestPass!2026"}
    )
    assert login.status_code == 200

    me = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    assert me.status_code == 200 and me.json()["email"] == "flow@arena.dev"

    refreshed = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert refreshed.status_code == 200 and refreshed.json()["access_token"]

    # An access token must not work as a refresh token (type claim).
    wrong_type = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["access_token"]}
    )
    assert wrong_type.status_code == 401


async def test_duplicate_email_409_and_wrong_password_401(client, register_user):
    await register_user()
    # Same email as the fixture user is unknown here; register twice directly.
    payload = {"email": "dup@arena.dev", "password": "TestPass!2026", "display_name": "Dup"}
    assert (await client.post("/api/v1/auth/register", json=payload)).status_code == 201
    assert (await client.post("/api/v1/auth/register", json=payload)).status_code == 409

    bad = await client.post(
        "/api/v1/auth/login", json={"email": "dup@arena.dev", "password": "WrongPass!1"}
    )
    assert bad.status_code == 401 and bad.json()["detail"] == "Invalid credentials"


async def test_unknown_email_gets_identical_generic_401(client):
    # AUD-18: the response must not distinguish unknown emails; timing
    # equalization itself is covered by the dummy-hash unit evidence.
    resp = await client.post(
        "/api/v1/auth/login", json={"email": "ghost@arena.dev", "password": "Whatever!1"}
    )
    assert resp.status_code == 401 and resp.json()["detail"] == "Invalid credentials"


async def test_profile_update_ignores_avatar_url(client, register_user):
    # AUD-17: avatar_url is no longer an accepted profile field.
    user_id, headers = await register_user()
    resp = await client.patch(
        "/api/v1/users/me/profile",
        headers=headers,
        json={"avatar_url": "https://evil.example/avatar.png", "bio": "hello"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["avatar_url"] is None
    assert body["bio"] == "hello"
    public = await client.get(f"/api/v1/users/{user_id}")
    assert public.json()["avatar_url"] is None
