import os
import uuid
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.media_file import MediaFile

POST_MEDIA_ROOT = Path(__file__).resolve().parent.parent.parent / "storage" / "posts"
AVATAR_MEDIA_ROOT = Path(__file__).resolve().parent.parent.parent / "storage" / "avatars"

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png"}
MAX_UPLOAD_BYTES = 8 * 1024 * 1024

# Storage backend selection. Default "fs" keeps the original behaviour
# (bytes on local disk, served via the /media static mount) used by the
# long-running-server track. "db" (Vercel track, whose filesystem is
# ephemeral) persists bytes in the media_files table instead.
# Read at call time so tests and serverless invocations always see the
# environment they were actually started with.
_MEDIA_REF_PREFIX = "media:"


def media_backend() -> str:
    return os.environ.get("MEDIA_BACKEND", "fs").strip().lower()


def media_ref(media_id: UUID | str) -> str:
    """Reference stored in Post.image_path for DB-backed post images."""
    return f"{_MEDIA_REF_PREFIX}{media_id}"


def is_media_ref(value: str | None) -> bool:
    return bool(value) and value.startswith(_MEDIA_REF_PREFIX)


def parse_media_ref(value: str) -> str:
    return value[len(_MEDIA_REF_PREFIX):]


async def _save_media_db(
    db: AsyncSession, file_bytes: bytes, content_type: str
) -> MediaFile:
    media = MediaFile(content_type=content_type, data=file_bytes)
    db.add(media)
    await db.flush()
    return media


async def save_post_image_db(
    db: AsyncSession, file_bytes: bytes, content_type: str
) -> str:
    media = await _save_media_db(db, file_bytes, content_type)
    return str(media.id)


async def save_avatar_image_db(
    db: AsyncSession, file_bytes: bytes, content_type: str
) -> str:
    media = await _save_media_db(db, file_bytes, content_type)
    return str(media.id)


async def get_media_file(db: AsyncSession, media_id: str) -> MediaFile | None:
    try:
        media_uuid = UUID(media_id)
    except (ValueError, AttributeError):
        return None
    result = await db.execute(select(MediaFile).where(MediaFile.id == media_uuid))
    return result.scalar_one_or_none()


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
