"""Phase 2 (2026-11-02): in-app invites and ELO challenge matches.

Two invite kinds share one inbox:
- MatchInvite: player -> player. Accepting creates a ChallengeMatch whose
  confirmed result moves ELO exactly like a tournament match (same helpers
  in app.api.v1.matches), guarded by anti-farming rules in the API layer
  (one open challenge per pair, 24h pair cooldown, 5/day player cap).
- TournamentInvite: organizer -> player for a registration_open tournament.
  Accepting joins the tournament (same checks as the public join endpoint).

ChallengeMatch mirrors Match's result lifecycle (ready -> result_submitted
-> completed | disputed -> completed) but is deliberately a separate table:
Match.tournament_id is NOT NULL and its finalize path advances brackets and
distributes prizes, none of which exists for a 1v1 challenge.
"""
from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, LargeBinary, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column


from app.db.session import Base


class InviteStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    CANCELLED = "cancelled"
    # "expired" is never stored: reads compute it from created_at so an old
    # pending row can never be accepted by a stale client.


class ChallengeStatus(str, Enum):
    READY = "ready"
    RESULT_SUBMITTED = "result_submitted"
    DISPUTED = "disputed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class MatchInvite(Base):
    __tablename__ = "match_invites"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    challenger_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    opponent_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=InviteStatus.PENDING)
    challenge_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("challenge_matches.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class TournamentInvite(Base):
    __tablename__ = "tournament_invites"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    tournament_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("tournaments.id", ondelete="CASCADE"), nullable=False
    )
    inviter_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    invitee_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=InviteStatus.PENDING)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ChallengeMatch(Base):
    __tablename__ = "challenge_matches"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    # No FK on invite_id: match_invites.challenge_id already points back at
    # this table, and a circular FK pair would need deferred constraints.
    # Integrity is structural anyway — the accept endpoint creates the
    # invite update and the challenge in a single transaction.
    invite_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False, unique=True)
    player_a_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    player_b_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(24), nullable=False, default=ChallengeStatus.READY)
    score_a: Mapped[int | None] = mapped_column(Integer, nullable=True)
    score_b: Mapped[int | None] = mapped_column(Integer, nullable=True)
    winner_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    disputed_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class ChallengeEvidence(Base):
    __tablename__ = "challenge_evidence"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    challenge_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("challenge_matches.id", ondelete="CASCADE"), nullable=False
    )
    submitted_by: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    claimed_score_a: Mapped[int] = mapped_column(Integer, nullable=False)
    claimed_score_b: Mapped[int] = mapped_column(Integer, nullable=False)
    image_path: Mapped[str] = mapped_column(String(500), nullable=False)
    image_data: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    ocr_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
