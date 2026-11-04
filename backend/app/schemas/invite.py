from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class PlayerBrief(BaseModel):
    user_id: UUID
    display_name: str
    avatar_url: str | None = None
    arena_no: int | None = None
    # Presence (migration 024): drives the online dot in the inbox.
    is_online: bool = False


class MatchInviteCreate(BaseModel):
    opponent_id: UUID


class MatchInviteRead(BaseModel):
    id: UUID
    challenger: PlayerBrief
    opponent: PlayerBrief
    status: str
    challenge_id: UUID | None = None
    created_at: datetime
    responded_at: datetime | None = None


class TournamentInviteCreate(BaseModel):
    tournament_id: UUID
    invitee_id: UUID


class TournamentInviteRead(BaseModel):
    id: UUID
    tournament_id: UUID
    tournament_name: str
    inviter: PlayerBrief
    invitee: PlayerBrief
    status: str
    created_at: datetime
    responded_at: datetime | None = None


class InviteInboxRead(BaseModel):
    match_received: list[MatchInviteRead]
    match_sent: list[MatchInviteRead]
    tournament_received: list[TournamentInviteRead]
    tournament_sent: list[TournamentInviteRead]


class InviteCountRead(BaseModel):
    pending_received: int


class ChallengeRead(BaseModel):
    id: UUID
    invite_id: UUID
    player_a: PlayerBrief
    player_b: PlayerBrief
    status: str
    score_a: int | None = None
    score_b: int | None = None
    winner_id: UUID | None = None
    disputed_by: UUID | None = None
    # Latest claimed result awaiting the other player's decision.
    pending_submitted_by: UUID | None = None
    pending_score_a: int | None = None
    pending_score_b: int | None = None
    pending_evidence_id: UUID | None = None
    completed_at: datetime | None = None
    created_at: datetime


class ChallengeEvidenceRead(BaseModel):
    id: UUID
    challenge_id: UUID
    submitted_by: UUID
    claimed_score_a: int
    claimed_score_b: int
    created_at: datetime

    model_config = {"from_attributes": True}
