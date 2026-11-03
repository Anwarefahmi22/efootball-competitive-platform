from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.tournament import Tournament
    from app.models.user import User


class TournamentRoom(Base):
    """A tournament's members-only discussion room («مجموعة البطولة»).

    Deliberately NOT named "group": ``Group`` in this codebase is the
    competitive group stage. A room belongs to exactly one tournament
    and dies with it — the FK cascade removes the room (and, through
    RoomMessage.room_id, its messages) when the tournament is deleted;
    stored image bytes are removed by ``core.rooms`` helpers, mirroring
    how post deletion cleans media.
    """

    __tablename__ = "tournament_rooms"
    __table_args__ = (
        UniqueConstraint("tournament_id", name="uq_tournament_rooms_tournament"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    tournament_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("tournaments.id", ondelete="CASCADE"), nullable=False
    )
    created_by: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    tournament: Mapped["Tournament"] = relationship()
    messages: Mapped[list["RoomMessage"]] = relationship(
        back_populates="room", cascade="all, delete-orphan"
    )


class RoomMessage(Base):
    """One message in a tournament room: text, a photo, or both.

    ``image_path`` follows the Post convention exactly: a ``media:<id>``
    reference when MEDIA_BACKEND=db, otherwise a filesystem path.
    """

    __tablename__ = "room_messages"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    room_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("tournament_rooms.id", ondelete="CASCADE"), nullable=False
    )
    author_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    room: Mapped["TournamentRoom"] = relationship(back_populates="messages")
    author: Mapped["User"] = relationship()
