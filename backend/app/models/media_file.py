from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, LargeBinary, String, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class MediaFile(Base):
    """User-uploaded media (post images, avatars) stored as DB bytes.

    Used only when MEDIA_BACKEND=db (the Vercel track): serverless
    filesystems are ephemeral, so — exactly like MatchEvidence — the bytes
    live in Postgres and are served back by id at /media/<id>. On the
    default MEDIA_BACKEND=fs track this table simply stays empty.
    """

    __tablename__ = "media_files"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    data: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
