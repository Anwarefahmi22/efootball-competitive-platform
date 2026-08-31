import uuid
from pathlib import Path

STORAGE_ROOT = Path(__file__).resolve().parent.parent.parent / "storage" / "evidence"

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png"}
MAX_UPLOAD_BYTES = 8 * 1024 * 1024  # 8 MB


def ensure_storage_dir() -> None:
    STORAGE_ROOT.mkdir(parents=True, exist_ok=True)


def save_evidence_image(match_id: str, file_bytes: bytes, extension: str) -> str:
    ensure_storage_dir()
    filename = f"{match_id}_{uuid.uuid4().hex}{extension}"
    path = STORAGE_ROOT / filename
    with open(path, "wb") as f:
        f.write(file_bytes)
    return str(path)
