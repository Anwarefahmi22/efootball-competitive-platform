"""AUD-12 / AUD-16 endpoint integration: streamed size caps and real
image decoding on the avatar and challenge-evidence upload paths."""
import io

import pytest
from PIL import Image

pytestmark = pytest.mark.asyncio


def _png(width=64, height=64) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (width, height), (20, 140, 60)).save(buf, "PNG")
    return buf.getvalue()


async def test_avatar_upload_normalizes_to_webp(client, register_user):
    _, headers = await register_user()
    resp = await client.post(
        "/api/v1/users/me/avatar",
        headers=headers,
        files={"image": ("me.png", _png(), "image/png")},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["avatar_url"].split("?")[0].endswith(".webp")


async def test_avatar_upload_rejects_non_image_bytes(client, register_user):
    _, headers = await register_user()
    resp = await client.post(
        "/api/v1/users/me/avatar",
        headers=headers,
        files={"image": ("me.png", b"<html>definitely not an image</html>", "image/png")},
    )
    assert resp.status_code == 400


async def test_avatar_upload_oversize_aborts_with_413(client, register_user):
    _, headers = await register_user()
    big = b"\x89PNG\r\n\x1a\n" + b"x" * (5 * 1024 * 1024 + 1)
    resp = await client.post(
        "/api/v1/users/me/avatar",
        headers=headers,
        files={"image": ("big.png", big, "image/png")},
    )
    assert resp.status_code == 413


async def test_challenge_evidence_requires_real_image(client, register_user):
    challenger_id, challenger_h = await register_user()
    opponent_id, opponent_h = await register_user()

    invite = await client.post(
        "/api/v1/invites/match", headers=challenger_h, json={"opponent_id": opponent_id}
    )
    assert invite.status_code == 201, invite.text
    accepted = await client.post(
        f"/api/v1/invites/match/{invite.json()['id']}/accept", headers=opponent_h
    )
    assert accepted.status_code == 201, accepted.text
    challenge_id = accepted.json()["id"]

    bad = await client.post(
        f"/api/v1/challenges/{challenge_id}/submit-result",
        headers=challenger_h,
        data={"score_a": "2", "score_b": "1"},
        files={"image": ("proof.png", b"not an image", "image/png")},
    )
    assert bad.status_code == 400

    good = await client.post(
        f"/api/v1/challenges/{challenge_id}/submit-result",
        headers=challenger_h,
        data={"score_a": "2", "score_b": "1"},
        files={"image": ("proof.png", _png(), "image/png")},
    )
    assert good.status_code == 201, good.text
