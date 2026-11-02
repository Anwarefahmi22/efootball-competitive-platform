"""AUD-01: authorization & ownership matrix (API level).

Mirrors the audit's Appendix A expectations on the routes that matter
most: nothing mutating is reachable anonymously, participants own the
match lifecycle, organizers own tournament control, admins own dispute
resolution and the admin surfaces.
"""
import io

import pytest
from PIL import Image

pytestmark = pytest.mark.asyncio
UNAUTH = (401, 403)  # HTTPBearer answers 403 for missing credentials


def _png() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (32, 32), (10, 10, 10)).save(buf, "PNG")
    return buf.getvalue()


async def test_anonymous_cannot_mutate_or_read_private_surfaces(client):
    assert (await client.post("/api/v1/tournaments", json={"name": "X", "max_participants": 2})).status_code in UNAUTH
    assert (await client.get("/api/v1/players/cards")).status_code in UNAUTH
    assert (await client.get("/api/v1/invites/count")).status_code in UNAUTH
    assert (await client.get("/api/v1/admin/disputes")).status_code in UNAUTH
    assert (await client.patch("/api/v1/users/me/profile", json={"bio": "x"})).status_code in UNAUTH


async def test_non_admin_cannot_reach_admin_surfaces(client, register_user):
    _, h = await register_user()
    assert (await client.get("/api/v1/admin/disputes", headers=h)).status_code == 403
    assert (await client.get("/api/v1/analytics/platform", headers=h)).status_code == 403
    assert (await client.post("/api/v1/seasons", headers=h, json={"name": "S1"})).status_code in (400, 403, 422)


async def test_outsider_cannot_touch_match_or_evidence(client, register_user):
    org_id, org_h = await register_user()
    p1_id, p1_h = await register_user()
    p2_id, p2_h = await register_user()
    outsider_id, outsider_h = await register_user()

    t = (await client.post(
        "/api/v1/tournaments", headers=org_h, json={"name": "Authz Cup", "max_participants": 4}
    )).json()
    p3_id, p3_h = await register_user()
    p4_id, p4_h = await register_user()
    roster = {p1_id: p1_h, p2_id: p2_h, p3_id: p3_h, p4_id: p4_h}
    for h in roster.values():
        await client.post(f"/api/v1/tournaments/{t['id']}/join", headers=h)
    await client.post(f"/api/v1/tournaments/{t['id']}/draw", headers=org_h)
    await client.post(f"/api/v1/tournaments/{t['id']}/start", headers=org_h)
    match = (await client.get(f"/api/v1/tournaments/{t['id']}/matches")).json()[0]

    # Outsider cannot submit a result.
    resp = await client.post(
        f"/api/v1/matches/{match['id']}/submit-result",
        headers=outsider_h,
        data={"score_a": "1", "score_b": "0"},
        files={"image": ("p.png", _png(), "image/png")},
    )
    assert resp.status_code == 403
    # Outsider cannot list evidence.
    assert (await client.get(f"/api/v1/matches/{match['id']}/evidence", headers=outsider_h)).status_code == 403
    # Non-organizer cannot draw or cancel someone else's tournament.
    assert (await client.post(f"/api/v1/tournaments/{t['id']}/draw", headers=outsider_h)).status_code == 403
    assert (await client.post(f"/api/v1/tournaments/{t['id']}/cancel", headers=outsider_h)).status_code == 403
    # The submitter cannot confirm their own result. (The draw is
    # random: take the headers of whoever player_a actually is.)
    submitter_h = roster[match["player_a_id"]]
    ok = await client.post(
        f"/api/v1/matches/{match['id']}/submit-result",
        headers=submitter_h,
        data={"score_a": "1", "score_b": "0"},
        files={"image": ("p.png", _png(), "image/png")},
    )
    assert ok.status_code == 201
    own_confirm = await client.post(f"/api/v1/matches/{match['id']}/confirm", headers=submitter_h)
    assert own_confirm.status_code in (400, 403)
