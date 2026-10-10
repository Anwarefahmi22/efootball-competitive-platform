"""Destructive E2E check for a disposable local/CI database.

Creates users and a tournament, then checks authentication, evidence storage,
mutual confirmation, and the winner. Never run against production.
"""
import io
import json
import urllib.error
import urllib.request
import uuid

BASE = "http://localhost:8000/api/v1"
REQUEST_TIMEOUT = 15
PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d494844520000000100000001080600000"
    "01f15c4890000000d49444154789c626001000000ffff030000060005"
    "57bfabd40000000049454e44ae426082"
)


def call(method, path, token=None, body=None, raw=None, content_type="application/json"):
    data = None
    headers = {}
    if raw is not None:
        data = raw
        headers["Content-Type"] = content_type
    elif body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as res:
            payload = res.read()
            try:
                return res.status, json.loads(payload)
            except (ValueError, UnicodeDecodeError):
                return res.status, payload
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode(errors="replace")
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError(f"{method} {path}: connection failed or timed out") from exc


def expect(method, path, expected=200, **kwargs):
    code, payload = call(method, path, **kwargs)
    allowed = (expected,) if isinstance(expected, int) else expected
    if code not in allowed:
        # Authentication responses contain tokens: do not print response bodies.
        raise AssertionError(f"{method} {path}: expected {allowed}, received {code}")
    return payload


suffix = uuid.uuid4().hex[:8]
email1 = f"e1_{suffix}@t.gg"
password = "Passw0rd!"
u1 = expect("POST", "/auth/register", expected=201, body={
    "email": email1, "password": password, "display_name": "P1",
})
u2 = expect("POST", "/auth/register", expected=201, body={
    "email": f"e2_{suffix}@t.gg", "password": password, "display_name": "P2",
})
assert u1.get("access_token") and u1.get("refresh_token"), "P1 token pair missing"
assert u2.get("access_token") and u2.get("refresh_token"), "P2 token pair missing"
t1, t2 = u1["access_token"], u2["access_token"]

owner = expect("GET", "/auth/me", token=t1)
login = expect("POST", "/auth/login", body={"email": email1, "password": password})
assert login.get("access_token") and login.get("refresh_token"), "login token pair missing"
login_user = expect("GET", "/auth/me", token=login["access_token"])
assert login_user["id"] == owner["id"], "login identity changed"
refreshed = expect("POST", "/auth/refresh", body={"refresh_token": login["refresh_token"]})
assert refreshed.get("access_token"), "refresh access token missing"
refresh_user = expect("GET", "/auth/me", token=refreshed["access_token"])
assert refresh_user["id"] == owner["id"], "refresh identity changed"
expect("POST", "/auth/login", expected=401, body={
    "email": email1, "password": "WrongPass!",
})
expect("POST", "/auth/refresh", expected=401, body={
    "refresh_token": login["access_token"],
})
expect("GET", "/auth/me", expected=401, token=login["refresh_token"])

tour = expect("POST", "/tournaments", expected=201, token=t1, body={
    "name": "E2E Cup", "max_participants": 4, "format": "single_elimination",
})
tid = tour["id"]
expect("POST", f"/tournaments/{tid}/join", expected=(200, 201, 204), token=t1)
expect("POST", f"/tournaments/{tid}/join", expected=(200, 201, 204), token=t2)
expect("POST", f"/tournaments/{tid}/draw", token=t1)
expect("POST", f"/tournaments/{tid}/start", token=t1)
matches = expect("GET", f"/tournaments/{tid}/matches")
assert isinstance(matches, list) and len(matches) == 1, "expected one final match"
m = matches[0]
mid = m["id"]
assert m["status"] == "ready", "final match is not ready"

boundary = "----e2e" + uuid.uuid4().hex
form = io.BytesIO()
for name, value in (("score_a", "2"), ("score_b", "1")):
    form.write((
        f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"'
        f"\r\n\r\n{value}\r\n"
    ).encode())
form.write((
    f'--{boundary}\r\nContent-Disposition: form-data; name="image"; '
    'filename="s.png"\r\nContent-Type: image/png\r\n\r\n'
).encode())
form.write(PNG)
form.write(f"\r\n--{boundary}--\r\n".encode())
ev = expect("POST", f"/matches/{mid}/submit-result", expected=201,
            token=t1, raw=form.getvalue(),
            content_type=f"multipart/form-data; boundary={boundary}")
img = expect("GET", f"/matches/{mid}/evidence/{ev['id']}/image", token=t2)
assert img == PNG, "image roundtrip from DB failed"
done = expect("POST", f"/matches/{mid}/confirm", token=t2)
assert done["status"] == "completed", "confirm did not complete the match"
t_after = expect("GET", f"/tournaments/{tid}")
assert t_after["status"] == "completed", "tournament not completed"
assert t_after["winner_id"] == m["player_a_id"], "winner does not match submitted score"
print("E2E OK: auth/login/refresh/token-types/tournament/evidence/confirm/winner")
