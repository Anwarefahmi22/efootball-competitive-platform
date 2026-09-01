from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class TournamentFormat(str, Enum):
    SINGLE_ELIMINATION = "single_elimination"
    LEAGUE = "league"
    GROUP_KNOCKOUT = "group_knockout"


class TournamentStatus(str, Enum):
    DRAFT = "draft"
    REGISTRATION_OPEN = "registration_open"
    REGISTRATION_CLOSED = "registration_closed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Tournament(Base):
    __tablename__ = "tournaments"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    format: Mapped[TournamentFormat] = mapped_column(
        String(32), nullable=False, default=TournamentFormat.SINGLE_ELIMINATION
    )
    status: Mapped[TournamentStatus] = mapped_column(
        String(32), nullable=False, default=TournamentStatus.REGISTRATION_OPEN
    )
    max_participants: Mapped[int] = mapped_column(Integer, nullable=False)
    entry_fee: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    prize_pool: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    prize_distributed: Mapped[bool] = mapped_column(nullable=False, default=False)
    draw_completed: Mapped[bool] = mapped_column(nullable=False, default=False)
    requires_approval: Mapped[bool] = mapped_column(nullable=False, default=False)
    num_groups: Mapped[int | None] = mapped_column(Integer, nullable=True)
    season_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("seasons.id"), nullable=True
    )
    created_by: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    participants: Mapped[list["TournamentParticipant"]] = relationship(
        back_populates="tournament", cascade="all, delete-orphan"
    )
    matches: Mapped[list["Match"]] = relationship(back_populates="tournament")  # noqa: F821


class TournamentParticipant(Base):
    __tablename__ = "tournament_participants"
    __table_args__ = (UniqueConstraint("tournament_id", "user_id", name="uq_tournament_user"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    tournament_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("tournaments.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    seed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="approved")
    group_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("groups.id"), nullable=True
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    tournament: Mapped[Tournament] = relationship(back_populates="participants")
    user: Mapped["User"] = relationship()  # noqa: F821
