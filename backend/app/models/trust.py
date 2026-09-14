from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
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


class TrustEventType(str, Enum):
    MATCH_CONFIRMED = "match_confirmed"
    DISPUTE_FILED = "dispute_filed"
    DISPUTE_RESOLVED = "dispute_resolved"


class TrustEvent(Base):
    """Append-only audit trail behind the aggregate counters on PlayerTrust.

    `PlayerTrust` can only ever describe a player's *current* state; it cannot
    say why it got there or who decided. Each row here is one consequence of
    one event, with the delta, the resulting score, and — for an administrative
    decision — the admin who made it.
    """

    __tablename__ = "trust_events"
    # One event of a given type per player per match. This is the guard that
    # makes "one administrative event -> one trust consequence" hold under
    # concurrent requests: the second writer's INSERT is rejected by the
    # database, not by an application-level check that could race.
    __table_args__ = (
        UniqueConstraint("user_id", "event_type", "match_id", name="uq_trust_event_once_per_match"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    event_type: Mapped[TrustEventType] = mapped_column(String(32), nullable=False)
    delta: Mapped[int] = mapped_column(Integer, nullable=False)
    trust_after: Mapped[int] = mapped_column(Integer, nullable=False)
    match_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("matches.id", ondelete="CASCADE"), nullable=False
    )
    actor_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
