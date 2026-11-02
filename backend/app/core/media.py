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


SQUAD_MEDIA_ROOT = Path(__file__).resolve().parent.parent.parent / "storage" / "squads"
ALLOWED_SQUAD_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
# Screenshots are wide (the standard eFootball squad shot is ~2048x930);
# 1600px keeps every rating legible while the WebP re-encode cuts the
# stored size by roughly two thirds at a quality the eye cannot tell
# apart on a phone-sized card.
SQUAD_MAX_WIDTH = 1600
SQUAD_WEBP_QUALITY = 85


def process_squad_image(file_bytes: bytes) -> bytes:
    """Re-encode an uploaded squad screenshot to compact WebP bytes.

    Raises ValueError for anything that is not a decodable image.
    Pillow is imported lazily so module import never depends on it.
    """
    import io

    from PIL import Image, ImageOps

    try:
        with Image.open(io.BytesIO(file_bytes)) as image:
            image = ImageOps.exif_transpose(image)
            image = image.convert("RGB")
            if image.width > SQUAD_MAX_WIDTH:
                height = round(image.height * SQUAD_MAX_WIDTH / image.width)
                image = image.resize((SQUAD_MAX_WIDTH, height), Image.LANCZOS)
            out = io.BytesIO()
            image.save(out, "WEBP", quality=SQUAD_WEBP_QUALITY, method=6)
            return out.getvalue()
    except Exception as exc:  # PIL raises many exception types on bad input
        raise ValueError("Undecodable image") from exc


async def save_squad_image_db(
    db: AsyncSession, file_bytes: bytes, content_type: str
) -> str:
    media = await _save_media_db(db, file_bytes, content_type)
    return str(media.id)


def save_squad_image(user_id: str, file_bytes: bytes) -> str:
    SQUAD_MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
    filename = f"{user_id}.webp"
    path = SQUAD_MEDIA_ROOT / filename
    with open(path, "wb") as f:
        f.write(file_bytes)
    return str(path)


def media_id_from_url(url: str | None) -> str | None:
    """Extract the media_files id from a stored '/media/<id>?v=...' URL."""
    if not url or not url.startswith("/media/"):
        return None
    tail = url[len("/media/"):].split("?")[0].split("/")[0]
    try:
        return str(UUID(tail))
    except (ValueError, AttributeError):
        return None


async def delete_media_db(db: AsyncSession, media_id: str | None) -> None:
    if not media_id:
        return
    media = await get_media_file(db, media_id)
    if media is not None:
        await db.delete(media)
        await db.flush()
