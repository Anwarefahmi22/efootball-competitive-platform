from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class PlayerTrust(Base):
    __tablename__ = "player_trust"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    trust_score: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    verified_matches: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    disputes_involved: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    false_reports: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unjustified_disputes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
