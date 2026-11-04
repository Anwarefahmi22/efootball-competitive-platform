"""Presence (migration 024): heartbeat -> online state, capped activity
accrual, and the presence_hidden privacy mask across payloads."""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import update

from app.db.session import AsyncSessionLocal
from app.models.user import User

pytestmark = pytest.mark.asyncio

PW = "Str0ng!Pass"


async def _register(client, email: str, name: str = "Present Player"):
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": PW, "display_name": name},
    )
    assert r.status_code == 201, r.text
    return r.json()


def _auth(pair) -> dict:
    return {"Authorization": f"Bearer {pair['access_token']}"}


async def _set_last_seen(user_id: str, when: datetime) -> None:
    async with AsyncSessionLocal() as db:
        await db.execute(
            update(User).where(User.id == user_id).values(last_seen_at=when)
        )
        await db.commit()


async def test_heartbeat_requires_auth(client):
    r = await client.post("/api/v1/users/me/heartbeat")
    assert r.status_code in (401, 403)


async def test_heartbeat_marks_online_and_accrues_capped(client):
    pair = await _register(client, "presence-a@arena.dev", "Presence A")
    headers = _auth(pair)

    me = await client.get("/api/v1/auth/me", headers=headers)
    uid = me.json()["id"]

    # Before any heartbeat: offline, never seen, zero activity.
    prof = (await client.get(f"/api/v1/users/{uid}", headers=headers)).json()
    assert prof["is_online"] is False
    assert prof["last_seen_at"] is None
    assert prof["active_seconds"] == 0

    r = await client.post("/api/v1/users/me/heartbeat", headers=headers)
    assert r.status_code == 204

    prof = (await client.get(f"/api/v1/users/{uid}", headers=headers)).json()
    assert prof["is_online"] is True
    assert prof["last_seen_at"] is not None

    # A heartbeat 45s after the previous one accrues ~45s of activity.
    await _set_last_seen(uid, datetime.now(timezone.utc) - timedelta(seconds=45))
    r = await client.post("/api/v1/users/me/heartbeat", headers=headers)
    assert r.status_code == 204
    prof = (await client.get(f"/api/v1/users/{uid}", headers=headers)).json()
    assert 40 <= prof["active_seconds"] <= 50

    # A heartbeat after a long absence accrues nothing (cap = 90s):
    # an abandoned tab must not inflate activity time.
    before = prof["active_seconds"]
    await _set_last_seen(uid, datetime.now(timezone.utc) - timedelta(minutes=10))
    await client.post("/api/v1/users/me/heartbeat", headers=headers)
    prof = (await client.get(f"/api/v1/users/{uid}", headers=headers)).json()
    assert prof["active_seconds"] == before
    # ...but the player is online again right after the fresh beat.
    assert prof["is_online"] is True

    # The Arena Star card carries the same presence view.
    cards = (await client.get("/api/v1/players/cards", headers=headers)).json()
    mine = next(c for c in cards if c["is_me"])
    assert mine["is_online"] is True
    assert mine["last_seen_at"] is not None


async def test_presence_hidden_masks_cards_and_profile(client):
    pair = await _register(client, "presence-b@arena.dev", "Presence B")
    headers = _auth(pair)
    uid = (await client.get("/api/v1/auth/me", headers=headers)).json()["id"]

    await client.post("/api/v1/users/me/heartbeat", headers=headers)
    prof = (await client.get(f"/api/v1/users/{uid}", headers=headers)).json()
    assert prof["is_online"] is True

    r = await client.patch(
        "/api/v1/users/me/profile",
        headers=headers,
        json={"presence_hidden": True},
    )
    assert r.status_code == 200, r.text
    assert r.json()["presence_hidden"] is True
    # The owner's own view is masked too (that is the point of hiding),
    # but the accumulated activity itself is not erased.
    assert r.json()["is_online"] is False
    assert r.json()["last_seen_at"] is None

    prof = (await client.get(f"/api/v1/users/{uid}", headers=headers)).json()
    assert prof["is_online"] is False
    assert prof["last_seen_at"] is None

    cards = (await client.get("/api/v1/players/cards", headers=headers)).json()
    mine = next(c for c in cards if c["is_me"])
    assert mine["is_online"] is False
    assert mine["last_seen_at"] is None

    # Un-hiding restores visibility of the (still fresh) heartbeat.
    r = await client.patch(
        "/api/v1/users/me/profile",
        headers=headers,
        json={"presence_hidden": False},
    )
    assert r.status_code == 200
    prof = (await client.get(f"/api/v1/users/{uid}", headers=headers)).json()
    assert prof["is_online"] is True
    assert prof["last_seen_at"] is not None
