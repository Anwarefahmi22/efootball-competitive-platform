"""AUD-01: end-to-end competitive lifecycles over the real HTTP stack.

These are the same flows the audit verified by hand with disposable
accounts (submit -> confirm -> ELO 1016/984; dispute -> admin resolve),
now repeatable against a disposable PostgreSQL database.

Note: the API requires single-elimination tournaments to seat a power
of two between 4 and 64, so tournament flows here run with 4 players
and assert on the first semifinal.
"""
import io

import pytest
from PIL import Image

pytestmark = pytest.mark.asyncio


def _png() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (64, 64), (20, 140, 60)).save(buf, "PNG")
    return buf.getvalue()


async def _roster(register_user, n=4):
    """Register n players; returns {user_id: headers}."""
    out = {}
    for _ in range(n):
        uid, h = await register_user()
        out[uid] = h
    return out


async def _make_tournament(client, org_h, *, cap=4, **kw):
    resp = await client.post(
        "/api/v1/tournaments",
        headers=org_h,
        json={"name": kw.pop("name", "Cup"), "max_participants": cap, **kw},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _started_matches(client, org_h, roster):
    """4-player single-elimination tournament, drawn and started."""
    t = await _make_tournament(client, org_h)
    for h in roster.values():
        r = await client.post(f"/api/v1/tournaments/{t['id']}/join", headers=h)
        assert r.status_code == 200, r.text
    r = await client.post(f"/api/v1/tournaments/{t['id']}/draw", headers=org_h)
    assert r.status_code == 200, r.text
    r = await client.post(f"/api/v1/tournaments/{t['id']}/start", headers=org_h)
    assert r.status_code == 200, r.text
    all_matches = (await client.get(f"/api/v1/tournaments/{t['id']}/matches")).json()
    # The bracket pre-creates the final with empty player slots; the two
    # semifinals are the playable matches.
    matches = [m for m in all_matches if m["player_a_id"] and m["player_b_id"]]
    assert len(matches) == 2
    return t, matches


async def _submit(client, match_id, headers, a=2, b=1):
    return await client.post(
        f"/api/v1/matches/{match_id}/submit-result",
        headers=headers,
        data={"score_a": str(a), "score_b": str(b)},
        files={"image": ("proof.png", _png(), "image/png")},
    )


async def _elo_map(client):
    board = (await client.get("/api/v1/ratings/leaderboard")).json()
    return {row["user_id"]: row["rating"] for row in board}


def _sides(match, roster):
    """(submitter_id, submitter_h, opponent_id, opponent_h) — player_a submits."""
    a, b = match["player_a_id"], match["player_b_id"]
    return a, roster[a], b, roster[b]


async def test_match_confirm_flow_applies_elo_exactly_once(client, register_user):
    _, org_h = await register_user()
    roster = await _roster(register_user)
    _, matches = await _started_matches(client, org_h, roster)
    match = matches[0]
    sub_id, sub_h, opp_id, opp_h = _sides(match, roster)

    resp = await _submit(client, match["id"], sub_h, 2, 1)
    assert resp.status_code == 201, resp.text

    confirm = await client.post(f"/api/v1/matches/{match['id']}/confirm", headers=opp_h)
    assert confirm.status_code == 200, confirm.text
    assert confirm.json()["status"] == "completed"
    assert confirm.json()["winner_id"] == sub_id

    elos = await _elo_map(client)
    assert elos[sub_id] == 1016
    assert elos[opp_id] == 984

    # Exactly-once: a second confirm is rejected and ELO does not move again.
    again = await client.post(f"/api/v1/matches/{match['id']}/confirm", headers=opp_h)
    assert again.status_code == 400
    assert (await _elo_map(client)) == elos

    trust = await client.get(f"/api/v1/trust/{sub_id}")
    assert trust.status_code == 200 and trust.json()["trust_score"] == 100


async def test_match_dispute_then_admin_resolve(client, register_user):
    from sqlalchemy import text

    from app.db.session import AsyncSessionLocal

    _, org_h = await register_user()
    roster = await _roster(register_user)
    admin_id, admin_h = await register_user()
    async with AsyncSessionLocal() as db:
        await db.execute(
            text("UPDATE users SET is_admin = true WHERE id = :id"), {"id": admin_id}
        )
        await db.commit()

    _, matches = await _started_matches(client, org_h, roster)
    match = matches[0]
    sub_id, sub_h, opp_id, opp_h = _sides(match, roster)

    assert (await _submit(client, match["id"], sub_h, 3, 0)).status_code == 201
    dispute = await client.post(
        f"/api/v1/matches/{match['id']}/dispute",
        headers=opp_h,
        json={"reason": "النتيجة غير صحيحة"},
    )
    assert dispute.status_code == 200, dispute.text
    assert dispute.json()["status"] == "disputed"
    assert await _elo_map(client) == {}  # no ELO moved while disputed

    denied = await client.post(
        f"/api/v1/matches/{match['id']}/resolve-dispute",
        headers=opp_h,
        json={"score_a": 3, "score_b": 0},
    )
    assert denied.status_code == 403

    resolved = await client.post(
        f"/api/v1/matches/{match['id']}/resolve-dispute",
        headers=admin_h,
        json={"score_a": 3, "score_b": 0},
    )
    assert resolved.status_code == 200, resolved.text
    elos = await _elo_map(client)
    assert elos[sub_id] == 1016 and elos[opp_id] == 984


async def test_challenge_flow_and_anti_farming(client, register_user):
    a_id, a_h = await register_user()
    b_id, b_h = await register_user()

    self_invite = await client.post(
        "/api/v1/invites/match", headers=a_h, json={"opponent_id": a_id}
    )
    assert self_invite.status_code == 422

    invite = await client.post(
        "/api/v1/invites/match", headers=a_h, json={"opponent_id": b_id}
    )
    assert invite.status_code == 201, invite.text
    accepted = await client.post(
        f"/api/v1/invites/match/{invite.json()['id']}/accept", headers=b_h
    )
    assert accepted.status_code == 201, accepted.text
    challenge_id = accepted.json()["id"]

    # One open challenge per pair: a second invite is refused.
    second = await client.post(
        "/api/v1/invites/match", headers=a_h, json={"opponent_id": b_id}
    )
    assert second.status_code == 409

    submit = await client.post(
        f"/api/v1/challenges/{challenge_id}/submit-result",
        headers=a_h,
        data={"score_a": "2", "score_b": "1"},
        files={"image": ("proof.png", _png(), "image/png")},
    )
    assert submit.status_code == 201, submit.text
    confirm = await client.post(f"/api/v1/challenges/{challenge_id}/confirm", headers=b_h)
    assert confirm.status_code == 200, confirm.text

    cards = (await client.get("/api/v1/players/cards", headers=a_h)).json()
    elo = {c["user_id"]: c["rating"] for c in cards}
    assert elo[a_id] == 1016 and elo[b_id] == 984


async def test_score_cap_rejected_in_both_submit_paths(client, register_user):
    # AUD-25 boundary: 31 is rejected before any state change, in the
    # challenge path here and the tournament path below.
    a_id, a_h = await register_user()
    b_id, b_h = await register_user()
    invite = await client.post("/api/v1/invites/match", headers=a_h, json={"opponent_id": b_id})
    accepted = await client.post(
        f"/api/v1/invites/match/{invite.json()['id']}/accept", headers=b_h
    )
    challenge_id = accepted.json()["id"]
    resp = await client.post(
        f"/api/v1/challenges/{challenge_id}/submit-result",
        headers=a_h,
        data={"score_a": "31", "score_b": "0"},
        files={"image": ("proof.png", _png(), "image/png")},
    )
    assert resp.status_code == 400

    _, org_h = await register_user()
    roster = await _roster(register_user)
    _, matches = await _started_matches(client, org_h, roster)
    match = matches[0]
    resp = await _submit(client, match["id"], roster[match["player_a_id"]], 0, 31)
    assert resp.status_code == 400


async def test_tournament_approval_flow_and_cancel(client, register_user):
    _, org_h = await register_user()
    roster = await _roster(register_user, n=2)
    ids = list(roster)
    t = await _make_tournament(client, org_h, requires_approval=True)
    for h in roster.values():
        assert (await client.post(f"/api/v1/tournaments/{t['id']}/join", headers=h)).status_code == 200
    # Draw with nobody approved yet fails.
    assert (await client.post(f"/api/v1/tournaments/{t['id']}/draw", headers=org_h)).status_code == 400
    for uid in ids:
        r = await client.post(
            f"/api/v1/tournaments/{t['id']}/participants/{uid}/approve", headers=org_h
        )
        assert r.status_code == 200, r.text
    drawn = await client.post(f"/api/v1/tournaments/{t['id']}/draw", headers=org_h)
    assert drawn.status_code == 200
    # Draw is idempotent-guarded: a second draw is a controlled error.
    assert (await client.post(f"/api/v1/tournaments/{t['id']}/draw", headers=org_h)).status_code == 400

    t2 = await _make_tournament(client, org_h, name="To Cancel")
    cancelled = await client.post(f"/api/v1/tournaments/{t2['id']}/cancel", headers=org_h)
    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()["status"] == "cancelled"
    join_late = await client.post(f"/api/v1/tournaments/{t2['id']}/join", headers=roster[ids[0]])
    assert join_late.status_code == 400
