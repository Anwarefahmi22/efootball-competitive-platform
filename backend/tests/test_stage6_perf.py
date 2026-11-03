"""Stage 6 acceptance tests: AUD-03 (cards pagination) and AUD-05
(invites no longer scale queries with inbox size)."""
import pytest
from sqlalchemy import event

from app.db.session import engine

pytestmark = pytest.mark.asyncio


async def test_cards_pagination_tiles_the_full_ordered_list(client, register_user):
    ids = []
    for _ in range(5):
        uid, _h = await register_user()
        ids.append(uid)
    _, viewer_h = await register_user()

    full = (await client.get("/api/v1/players/cards?limit=100", headers=viewer_h)).json()
    assert len(full) == 6
    arena_order = [c["arena_no"] for c in full]
    assert arena_order == sorted(arena_order)  # all at 1000 ELO -> arena_no asc

    page1 = (await client.get("/api/v1/players/cards?limit=2&offset=0", headers=viewer_h)).json()
    page2 = (await client.get("/api/v1/players/cards?limit=2&offset=2", headers=viewer_h)).json()
    page3 = (await client.get("/api/v1/players/cards?limit=2&offset=4", headers=viewer_h)).json()
    assert [len(p) for p in (page1, page2, page3)] == [2, 2, 2]
    tiled = page1 + page2 + page3
    assert [c["user_id"] for c in tiled] == [c["user_id"] for c in full]
    # Defaults stay bounded and sane.
    default = (await client.get("/api/v1/players/cards", headers=viewer_h)).json()
    assert len(default) == 6
    bad = await client.get("/api/v1/players/cards?limit=0", headers=viewer_h)
    assert bad.status_code == 422


class _QueryCounter:
    def __init__(self):
        self.count = 0

    def __call__(self, conn, cursor, statement, parameters, context, executemany):
        self.count += 1


async def test_inbox_query_count_is_constant_in_inbox_size(client, register_user):
    recipient_id, recipient_h = await register_user()
    senders = []
    for _ in range(6):
        sid, sh = await register_user()
        senders.append((sid, sh))
        resp = await client.post(
            "/api/v1/invites/match", headers=sh, json={"opponent_id": recipient_id}
        )
        assert resp.status_code == 201, resp.text

    counter = _QueryCounter()
    event.listen(engine.sync_engine, "before_cursor_execute", counter)
    try:
        inbox = await client.get("/api/v1/invites", headers=recipient_h)
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", counter)
    assert inbox.status_code == 200, inbox.text
    received = inbox.json()["match_received"]
    assert len(received) == 6
    # Brief contents survived the batch refactor.
    names = {row["challenger"]["display_name"] for row in received}
    assert len(names) == 6
    assert all(row["challenger"]["arena_no"] for row in received)
    # 4 list queries + a constant number of batch loads. The per-invite
    # loader this replaced needed 2 queries per brief (24+ here).
    assert counter.count <= 12, f"inbox used {counter.count} queries for 6 invites"


async def test_challenge_list_query_count_is_bounded(client, register_user):
    a_id, a_h = await register_user()
    b_id, b_h = await register_user()
    invite = await client.post("/api/v1/invites/match", headers=a_h, json={"opponent_id": b_id})
    accepted = await client.post(
        f"/api/v1/invites/match/{invite.json()['id']}/accept", headers=b_h
    )
    assert accepted.status_code == 201

    counter = _QueryCounter()
    event.listen(engine.sync_engine, "before_cursor_execute", counter)
    try:
        rows = await client.get("/api/v1/challenges", headers=a_h)
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", counter)
    assert rows.status_code == 200
    assert len(rows.json()) == 1
    assert rows.json()[0]["player_a"]["arena_no"] is not None
    assert counter.count <= 8, f"challenge list used {counter.count} queries"
