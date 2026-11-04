from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Identity, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    phone: Mapped[str | None] = mapped_column(String(32), unique=True, index=True, nullable=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Email ownership proof (verification-code flow, migration 023).
    # Deliberately separate from ``is_verified`` — that flag is the
    # admin-granted identity badge shown on Arena Star cards.
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Public sequential player number shown on the Arena Star card
    # (ARENA ID #1001+). Database identity column — see migration 017.
    arena_no: Mapped[int] = mapped_column(
        BigInteger, Identity(start=1001), unique=True, nullable=False
    )
    # Presence (migration 024): last heartbeat stamp, accumulated real
    # activity seconds (capped-gap accrual — see app.core.presence) and
    # the player's own switch to hide their online state from others.
    last_seen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    active_seconds: Mapped[int] = mapped_column(
        BigInteger, default=0, server_default="0", nullable=False
    )
    presence_hidden: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    profile: Mapped["Profile"] = relationship(back_populates="user", uselist=False)


class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    country: Mapped[str | None] = mapped_column(String(64), nullable=True)
    efootball_ign: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # Arena Star card squad block (drawn, not an uploaded image): the
    # formation label (e.g. "4-3-3") and the squad's collective strength.
    formation: Mapped[str | None] = mapped_column(String(16), nullable=True)
    squad_strength: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Uploaded eFootball squad screenshot (migration 018), stored like the
    # avatar: a /media/<id> URL on the DB track, a storage path on fs.
    squad_image_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user: Mapped["User"] = relationship(back_populates="profile")
