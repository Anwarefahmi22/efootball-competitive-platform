"""Server-side refresh-token sessions (AUD-10).

Until this table existed, a refresh token was an unstoppable 7-day
JWT: no rotation, no revocation, no logout. Each row tracks one
refresh token by its JWT ``jti``:

- ``family_id`` groups every token descended from one login. Rotation
  keeps the family; reuse of a rotated token revokes the whole family.
- ``token_hash`` is the SHA-256 of the token — the raw token is never
  stored, so a database leak does not leak usable sessions.
- ``rotated_at`` / ``replaced_by_id`` record the rotation chain;
  ``revoked_at`` records logout, reuse-detection, or admin action.
"""
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class RefreshSession(Base):
    __tablename__ = "refresh_sessions"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    family_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    rotated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    replaced_by_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
