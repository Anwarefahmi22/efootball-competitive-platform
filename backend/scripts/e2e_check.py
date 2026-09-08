"""Quick E2E check run inside the API container:
register 2 users -> tournament -> join -> draw -> start -> submit result
(with image) -> confirm -> fetch image back from DB.
"""
import io
import json
import mimetypes
import time
import urllib.error
import urllib.request
import uuid

BASE = "http://localhost:8000/api/v1"
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
        with urllib.request.urlopen(req) as res:
            payload = res.read()
            try:
                return res.status, json.loads(payload)
            except Exception:
                return res.status, payload
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace")


suffix = uuid.uuid4().hex[:8]
_, u1 = call("POST", "/auth/register", body={"email": f"e1_{suffix}@t.gg", "password": "Passw0rd!", "display_name": "P1"})
_, u2 = call("POST", "/auth/register", body={"email": f"e2_{suffix}@t.gg", "password": "Passw0rd!", "display_name": "P2"})
t1, t2 = u1["access_token"], u2["access_token"]

_, tour = call("POST", "/tournaments", token=t1, body={"name": "E2E Cup", "max_participants": 4, "format": "single_elimination"})
tid = tour["id"]
call("POST", f"/tournaments/{tid}/join", token=t1)
call("POST", f"/tournaments/{tid}/join", token=t2)
assert call("POST", f"/tournaments/{tid}/draw", token=t1)[0] == 200, "draw failed"
assert call("POST", f"/tournaments/{tid}/start", token=t1)[0] == 200, "start failed"

_, matches = call("GET", f"/tournaments/{tid}/matches")
m = matches[0]
mid = m["id"]

boundary = "----e2e" + uuid.uuid4().hex
form = io.BytesIO()
form.write(f"--{boundary}\r\nContent-Disposition: form-data; name=\"score_a\"\r\n\r\n2\r\n".encode())
form.write(f"--{boundary}\r\nContent-Disposition: form-data; name=\"score_b\"\r\n\r\n1\r\n".encode())
form.write(f"--{boundary}\r\nContent-Disposition: form-data; name=\"image\"; filename=\"s.png\"\r\nContent-Type: image/png\r\n\r\n".encode())
form.write(PNG)
form.write(f"\r\n--{boundary}--\r\n".encode())

st, ev = call("POST", f"/matches/{mid}/submit-result", token=t1, raw=form.getvalue(),
              content_type=f"multipart/form-data; boundary={boundary}")
assert st == 201, f"submit failed: {st} {ev}"

st, img = call("GET", f"/matches/{mid}/evidence/{ev['id']}/image", token=t2)
assert st == 200 and img == PNG, "image roundtrip from DB failed"

st, done = call("POST", f"/matches/{mid}/confirm", token=t2)
assert st == 200 and done["status"] == "completed", "confirm failed"

_, t_after = call("GET", f"/tournaments/{tid}")
assert t_after["status"] == "completed" and t_after["winner_id"], "tournament not completed"
print("E2E OK: register/tournament/draw/start/evidence-in-db/confirm/winner")
