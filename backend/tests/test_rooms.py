"""Tournament rooms («مجموعة البطولة»): creation option, membership,
message rules, deletion cascades, and the 7-day inactivity purge."""
import io
from datetime import datetime, timedelta, timezone

import pytest
from PIL import Image
from sqlalchemy import select, text

from app.core.rooms import purge_inactive_rooms
from app.db.session import AsyncSessionLocal
from app.models.media_file import MediaFile
from app.models.room import TournamentRoom


def _png_bytes() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (64, 64), (20, 120, 60)).save(buf, format="PNG")
    return buf.getvalue()


async def _create_tournament(client, headers, **overrides):
    payload = {"name": "Room Cup", "max_participants": 8}
    payload.update(overrides)
    resp = await client.post("/api/v1/tournaments", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _room(client, headers, tournament_id):
    resp = await client.get(f"/api/v1/tournaments/{tournament_id}/room", headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()


async def _post_message(client, headers, tournament_id, body="هدف رائع!", image=False):
    data = {}
    files = {}
    if body is not None:
        data["body"] = body
    if image:
        files["image"] = ("goal.png", _png_bytes(), "image/png")
    resp = await client.post(
        f"/api/v1/tournaments/{tournament_id}/room/messages",
        data=data,
        files=files or None,
        headers=headers,
    )
    return resp


@pytest.mark.asyncio
async def test_room_created_by_default_and_opt_out(client, register_user):
    organizer_id, organizer_h = await register_user()

    tournament = await _create_tournament(client, organizer_h)
    room = await _room(client, organizer_h, tournament["id"])
    assert room["exists"] is True
    assert room["is_organizer"] is True
    assert room["is_member"] is True

    no_room = await _create_tournament(client, organizer_h, create_room=False)
    room2 = await _room(client, organizer_h, no_room["id"])
    assert room2["exists"] is False


@pytest.mark.asyncio
async def test_room_create_later_rules(client, register_user):
    organizer_id, organizer_h = await register_user()
    _, stranger_h = await register_user()
    tournament = await _create_tournament(client, organizer_h, create_room=False)
    tid = tournament["id"]

    # Only the organizer can open the group afterwards.
    resp = await client.post(f"/api/v1/tournaments/{tid}/room", headers=stranger_h)
    assert resp.status_code == 403
    resp = await client.post(f"/api/v1/tournaments/{tid}/room", headers=organizer_h)
    assert resp.status_code == 201
    assert resp.json()["exists"] is True
    # And only once.
    resp = await client.post(f"/api/v1/tournaments/{tid}/room", headers=organizer_h)
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_membership_gates_messages(client, register_user):
    organizer_id, organizer_h = await register_user()
    member_id, member_h = await register_user()
    _, stranger_h = await register_user()
    tournament = await _create_tournament(client, organizer_h)
    tid = tournament["id"]

    # Stranger: room state is visible, messages are not.
    state = await _room(client, stranger_h, tid)
    assert state["exists"] is True and state["is_member"] is False
    resp = await client.get(f"/api/v1/tournaments/{tid}/room/messages", headers=stranger_h)
    assert resp.status_code == 403
    resp = await _post_message(client, stranger_h, tid)
    assert resp.status_code == 403

    # Joining (approved) unlocks the group.
    resp = await client.post(f"/api/v1/tournaments/{tid}/join", headers=member_h)
    assert resp.status_code == 200, resp.text
    resp = await _post_message(client, member_h, tid)
    assert resp.status_code == 201, resp.text
    resp = await client.get(f"/api/v1/tournaments/{tid}/room/messages", headers=member_h)
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["author_id"] == member_id


@pytest.mark.asyncio
async def test_pending_participant_is_not_a_member(client, register_user):
    organizer_id, organizer_h = await register_user()
    _, pending_h = await register_user()
    tournament = await _create_tournament(client, organizer_h, requires_approval=True)
    tid = tournament["id"]
    resp = await client.post(f"/api/v1/tournaments/{tid}/join", headers=pending_h)
    assert resp.status_code == 200, resp.text
    resp = await client.get(f"/api/v1/tournaments/{tid}/room/messages", headers=pending_h)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_message_photo_and_delete_rules(client, register_user, monkeypatch):
    monkeypatch.setenv("MEDIA_BACKEND", "db")
    organizer_id, organizer_h = await register_user()
    member_id, member_h = await register_user()
    tournament = await _create_tournament(client, organizer_h)
    tid = tournament["id"]
    await client.post(f"/api/v1/tournaments/{tid}/join", headers=member_h)

    # A photo message lands in media_files (db backend).
    resp = await _post_message(client, member_h, tid, body=None, image=True)
    assert resp.status_code == 201, resp.text
    message = resp.json()
    assert message["has_image"] is True
    async with AsyncSessionLocal() as db:
        count = (await db.execute(select(MediaFile))).scalars().all()
        assert len(count) == 1

    # Members can fetch the photo; the message lists with can_delete set
    # only for its author (and the organizer).
    resp = await client.get(
        f"/api/v1/tournaments/{tid}/room/messages/{message['id']}/image", headers=organizer_h
    )
    assert resp.status_code == 200
    listed = (await client.get(f"/api/v1/tournaments/{tid}/room/messages", headers=member_h)).json()
    assert listed[0]["can_delete"] is True
    listed_org = (await client.get(f"/api/v1/tournaments/{tid}/room/messages", headers=organizer_h)).json()
    assert listed_org[0]["can_delete"] is True

    # A random member cannot delete someone else's message; the
    # organizer can — and the stored photo row goes with it.
    _, other_h = await register_user()
    await client.post(f"/api/v1/tournaments/{tid}/join", headers=other_h)
    resp = await client.delete(
        f"/api/v1/tournaments/{tid}/room/messages/{message['id']}", headers=other_h
    )
    assert resp.status_code == 403
    resp = await client.delete(
        f"/api/v1/tournaments/{tid}/room/messages/{message['id']}", headers=organizer_h
    )
    assert resp.status_code == 204
    async with AsyncSessionLocal() as db:
        remaining = (await db.execute(select(MediaFile))).scalars().all()
        assert remaining == []


@pytest.mark.asyncio
async def test_room_delete_and_tournament_delete_cascade(client, register_user, monkeypatch):
    monkeypatch.setenv("MEDIA_BACKEND", "db")
    organizer_id, organizer_h = await register_user()

    # Organizer deletes the group: messages + photos go too.
    t1 = await _create_tournament(client, organizer_h)
    resp = await _post_message(client, organizer_h, t1["id"], image=True)
    assert resp.status_code == 201
    resp = await client.delete(f"/api/v1/tournaments/{t1['id']}/room", headers=organizer_h)
    assert resp.status_code == 204
    assert (await _room(client, organizer_h, t1["id"]))["exists"] is False
    async with AsyncSessionLocal() as db:
        assert (await db.execute(select(MediaFile))).scalars().all() == []
        assert (await db.execute(select(TournamentRoom))).scalars().all() == []

    # Deleting the tournament removes its group with everything in it.
    t2 = await _create_tournament(client, organizer_h)
    resp = await _post_message(client, organizer_h, t2["id"], image=True)
    assert resp.status_code == 201
    resp = await client.delete(f"/api/v1/tournaments/{t2['id']}", headers=organizer_h)
    assert resp.status_code == 204
    resp = await client.get(f"/api/v1/tournaments/{t2['id']}/room", headers=organizer_h)
    assert resp.status_code == 404
    async with AsyncSessionLocal() as db:
        assert (await db.execute(select(TournamentRoom))).scalars().all() == []
        assert (await db.execute(select(MediaFile))).scalars().all() == []


async def _backdate(tournament_id, room_id, *, days, message_days=None):
    old = datetime.now(timezone.utc) - timedelta(days=days)
    async with AsyncSessionLocal() as db:
        await db.execute(
            text("UPDATE tournaments SET updated_at = :ts WHERE id = :id"),
            {"ts": old, "id": tournament_id},
        )
        await db.execute(
            text("UPDATE tournament_rooms SET created_at = :ts WHERE id = :id"),
            {"ts": old, "id": room_id},
        )
        if message_days is not None:
            msg_old = datetime.now(timezone.utc) - timedelta(days=message_days)
            await db.execute(
                text("UPDATE room_messages SET created_at = :ts WHERE room_id = :id"),
                {"ts": msg_old, "id": room_id},
            )
        await db.commit()


@pytest.mark.asyncio
async def test_purge_after_seven_inactive_days(client, register_user):
    organizer_id, organizer_h = await register_user()

    # Fully silent for 8 days -> purged.
    t1 = await _create_tournament(client, organizer_h)
    room1 = await _room(client, organizer_h, t1["id"])
    await _post_message(client, organizer_h, t1["id"])
    await _backdate(t1["id"], room1["room_id"], days=8, message_days=8)

    # Silent tournament but a message yesterday -> conversation is
    # alive, the group must survive.
    t2 = await _create_tournament(client, organizer_h)
    room2 = await _room(client, organizer_h, t2["id"])
    await _post_message(client, organizer_h, t2["id"])
    await _backdate(t2["id"], room2["room_id"], days=8, message_days=1)

    purged = await purge_inactive_rooms()
    assert purged == 1
    assert (await _room(client, organizer_h, t1["id"]))["exists"] is False
    assert (await _room(client, organizer_h, t2["id"]))["exists"] is True
    # The tournament itself is untouched by the room purge.
    resp = await client.get(f"/api/v1/tournaments/{t1['id']}", headers=organizer_h)
    assert resp.status_code == 200
