import uuid
from pathlib import Path

POST_MEDIA_ROOT = Path(__file__).resolve().parent.parent.parent / "storage" / "posts"
AVATAR_MEDIA_ROOT = Path(__file__).resolve().parent.parent.parent / "storage" / "avatars"

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png"}
MAX_UPLOAD_BYTES = 8 * 1024 * 1024


def ensure_dir() -> None:
    POST_MEDIA_ROOT.mkdir(parents=True, exist_ok=True)


def save_post_image(file_bytes: bytes, extension: str) -> str:
    ensure_dir()
    filename = f"{uuid.uuid4().hex}{extension}"
    path = POST_MEDIA_ROOT / filename
    with open(path, "wb") as f:
        f.write(file_bytes)
    return str(path)


def save_avatar_image(user_id: str, file_bytes: bytes, extension: str) -> str:
    AVATAR_MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
    filename = f"{user_id}{extension}"
    path = AVATAR_MEDIA_ROOT / filename
    with open(path, "wb") as f:
        f.write(file_bytes)
    return str(path)
