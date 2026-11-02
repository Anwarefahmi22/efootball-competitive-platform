"""Stage 5 acceptance tests: AUD-07 (verify), AUD-08 (deletion),
AUD-28 (collusion signals include challenges + win split)."""
import pytest
from sqlalchemy import text

from app.db.session import AsyncSessionLocal

pytestmark = pytest.mark.asyncio


async def _make_admin(user_id) -> None:
    async with AsyncSessionLocal() as db:
        await db.execute(
            text("UPDATE users SET is_admin = true WHERE id = :id"), {"id": user_id}
        )
        await db.commit()


async def _post(client, headers, content="hello arena"):
    resp = await client.post("/api/v1/posts", headers=headers, data={"content": content})
    assert resp.status_code == 201, resp.text
    return resp.json()


# ------------------------------------------------------------------ AUD-07

async def test_admin_verify_unverify_flow(client, register_user):
    target_id, _ = await register_user()
    admin_id, admin_h = await register_user()
    plain_id, plain_h = await register_user()
    await _make_admin(admin_id)

    denied = await client.post(f"/api/v1/admin/users/{target_id}/verify", headers=plain_h)
    assert denied.status_code == 403

    missing = await client.post(
        "/api/v1/admin/users/00000000-0000-0000-0000-000000000000/verify", headers=admin_h
    )
    assert missing.status_code == 404

    verified = await client.post(f"/api/v1/admin/users/{target_id}/verify", headers=admin_h)
    assert verified.status_code == 200, verified.text
    assert verified.json()["is_verified"] is True
    # Idempotent.
    again = await client.post(f"/api/v1/admin/users/{target_id}/verify", headers=admin_h)
    assert again.status_code == 200 and again.json()["is_verified"] is True
    # The badge is real state: the Arena Star card shows it.
    cards = (await client.get("/api/v1/players/cards", headers=admin_h)).json()
    card = next(c for c in cards if c["user_id"] == target_id)
    assert card["is_verified"] is True

    unverified = await client.request(
        "DELETE", f"/api/v1/admin/users/{target_id}/verify", headers=admin_h
    )
    assert unverified.status_code == 200 and unverified.json()["is_verified"] is False

    # /auth/me now surfaces the admin flag for the UI.
    me = await client.get("/api/v1/auth/me", headers=admin_h)
    assert me.json()["is_admin"] is True
    me_plain = await client.get("/api/v1/auth/me", headers=plain_h)
    assert me_plain.json()["is_admin"] is False


# ------------------------------------------------------------------ AUD-08

async def test_post_and_comment_deletion_rules(client, register_user):
    author_id, author_h = await register_user()
    other_id, other_h = await register_user()
    admin_id, admin_h = await register_user()
    await _make_admin(admin_id)

    post = await _post(client, author_h)
    comment = await client.post(
        f"/api/v1/posts/{post['id']}/comments",
        headers=other_h,
        json={"content": "nice one"},
    )
    assert comment.status_code == 201, comment.text
    comment = comment.json()

    # A stranger can delete neither the comment nor the post.
    assert (
        await client.request("DELETE", f"/api/v1/posts/{post['id']}/comments/{comment['id']}", headers=author_h)
    ).status_code == 403
    assert (
        await client.request("DELETE", f"/api/v1/posts/{post['id']}", headers=other_h)
    ).status_code == 403

    # The comment author deletes their own comment.
    own = await client.request(
        "DELETE", f"/api/v1/posts/{post['id']}/comments/{comment['id']}", headers=other_h
    )
    assert own.status_code == 204
    remaining = await client.get(f"/api/v1/posts/{post['id']}/comments")
    assert remaining.json() == []

    # The post author deletes the post (comments/likes cascade).
    gone = await client.request("DELETE", f"/api/v1/posts/{post['id']}", headers=author_h)
    assert gone.status_code == 204
    assert (await client.get(f"/api/v1/posts/{post['id']}")).status_code == 404

    # An admin can delete someone else's post.
    post2 = await _post(client, author_h, "moderate me")
    mod = await client.request("DELETE", f"/api/v1/posts/{post2['id']}", headers=admin_h)
    assert mod.status_code == 204


# ------------------------------------------------------------------ AUD-28

async def _completed_challenge(client, a_h, a_id, b_h, b_id, score=(2, 1)):
    import io

    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (32, 32), (0, 128, 0)).save(buf, "PNG")
    invite = await client.post("/api/v1/invites/match", headers=a_h, json={"opponent_id": b_id})
    if invite.status_code == 429:  # pair cooldown from an earlier challenge
        return False
    assert invite.status_code == 201, invite.text
    accepted = await client.post(
        f"/api/v1/invites/match/{invite.json()['id']}/accept", headers=b_h
    )
    assert accepted.status_code == 201, accepted.text
    cid = accepted.json()["id"]
    submit = await client.post(
        f"/api/v1/challenges/{cid}/submit-result",
        headers=a_h,
        data={"score_a": str(score[0]), "score_b": str(score[1])},
        files={"image": ("p.png", buf.getvalue(), "image/png")},
    )
    assert submit.status_code == 201, submit.text
    confirm = await client.post(f"/api/v1/challenges/{cid}/confirm", headers=b_h)
    assert confirm.status_code == 200, confirm.text
    return True


async def test_collusion_signals_cover_challenges_with_win_split(client, register_user):
    from sqlalchemy import text as sql_text

    a_id, a_h = await register_user()
    b_id, b_h = await register_user()
    admin_id, admin_h = await register_user()
    await _make_admin(admin_id)

    # Non-admins never see the signals.
    assert (await client.get("/api/v1/fraud/collusion-candidates", headers=a_h)).status_code == 403

    # Three completed challenges, all won by A. The 24h pair cooldown
    # would block rematches, so rewind completed_at between rounds —
    # exactly the pattern a reviewer would want flagged.
    for round_no in range(3):
        assert await _completed_challenge(client, a_h, a_id, b_h, b_id)
        async with AsyncSessionLocal() as db:
            await db.execute(
                sql_text(
                    "UPDATE challenge_matches SET completed_at = completed_at - interval '25 hours' WHERE completed_at IS NOT NULL"
                )
            )
            await db.commit()

    signals = await client.get("/api/v1/fraud/collusion-candidates", headers=admin_h)
    assert signals.status_code == 200, signals.text
    rows = signals.json()
    assert len(rows) == 1
    row = rows[0]
    assert {row["player_a_id"], row["player_b_id"]} == {a_id, b_id}
    assert row["matches_together"] == 3
    assert row["challenges_together"] == 3
    assert row["a_wins"] + row["b_wins"] == 3
    assert max(row["a_wins"], row["b_wins"]) == 3  # fully one-sided
    # Signal only: nobody's trust or ELO was touched by reading it.
    trust = await client.get(f"/api/v1/trust/{a_id}")
    assert trust.json()["trust_score"] == 100
