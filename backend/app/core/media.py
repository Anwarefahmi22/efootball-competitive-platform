import os
import uuid
from pathlib import Path
from uuid import UUID

from fastapi import HTTPException, UploadFile, status
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


async def read_upload_limited(upload: UploadFile, max_bytes: int) -> bytes:
    """Stream an upload into memory, aborting the moment it exceeds the cap.

    AUD-12: the previous handlers did ``await upload.read()`` and only then
    compared lengths, so an arbitrarily large multipart body was fully
    buffered in a serverless function's RAM before being rejected. This
    reader counts chunks as they arrive and fails fast with 413.
    """
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await upload.read(64 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Uploaded file is too large",
            )
        chunks.append(chunk)
    return b"".join(chunks)


def normalize_image(
    file_bytes: bytes, *, max_width: int | None, quality: int = 85
) -> bytes:
    """Decode an uploaded image and re-encode it as WebP (AUD-16).

    The declared content type is never trusted: Pillow must actually
    decode the bytes. Anything undecodable raises ValueError. The
    re-encode strips metadata and any payload smuggled inside a valid
    image container. ``process_squad_image`` below is this same policy
    with the squad geometry.
    """
    import io

    from PIL import Image, ImageOps

    try:
        with Image.open(io.BytesIO(file_bytes)) as image:
            image = ImageOps.exif_transpose(image)
            image = image.convert("RGB")
            if max_width is not None and image.width > max_width:
                height = round(image.height * max_width / image.width)
                image = image.resize((max_width, height), Image.LANCZOS)
            out = io.BytesIO()
            image.save(out, "WEBP", quality=quality, method=6)
            return out.getvalue()
    except Exception as exc:  # PIL raises many exception types on bad input
        raise ValueError("Undecodable image") from exc


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


def evidence_media_type(image_path: str | None) -> str:
    """Content type for stored evidence bytes, by stored file extension.

    Legacy rows are .png/.jpg; rows written after the AUD-16 normalization
    are .webp. Anything else falls back to JPEG, matching the historical
    behaviour of the two evidence-image endpoints.
    """
    path = (image_path or "").lower()
    if path.endswith(".png"):
        return "image/png"
    if path.endswith(".webp"):
        return "image/webp"
    return "image/jpeg"


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
