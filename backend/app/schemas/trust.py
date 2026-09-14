from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class TrustPublic(BaseModel):
    user_id: UUID
    display_name: str
    trust_score: int
    verified_matches: int
    # Moderation data, not a public reputation signal: null for anyone who is
    # neither the player themself nor a platform admin (same pattern the
    # analytics endpoint already uses for wallet_balance).
    disputes_involved: int | None


class TrustEventRead(BaseModel):
    """One row of a player's trust audit trail."""

    id: UUID
    event_type: str
    delta: int
    trust_after: int
    match_id: UUID
    actor_id: UUID | None
    reason: str | None
    created_at: datetime


class CollusionCandidate(BaseModel):
    player_a_id: UUID
    player_a_name: str
    player_b_id: UUID
    player_b_name: str
    matches_together: int


class DisputeQueueItem(BaseModel):
    """One row of the admin dispute queue.

    Everything here is derived from data the platform already stores; nothing
    is inferred and no heuristic score is presented as a verdict.
    """

    match_id: UUID
    status: str
    tournament_id: UUID
    tournament_name: str
    tournament_format: str
    round_number: int
    player_a_id: UUID
    player_a_name: str
    player_a_trust: int
    player_b_id: UUID
    player_b_name: str
    player_b_trust: int
    submitted_by: UUID
    submitted_by_name: str
    claimed_score_a: int
    claimed_score_b: int
    disputed_by: UUID | None
    disputed_by_name: str | None
    evidence_count: int
    has_evidence: bool
    disputed_at: datetime


class DisputeDetail(DisputeQueueItem):
    """Queue row plus the evidence an admin needs in order to decide."""

    evidence: list["DisputeEvidenceRead"]
    collusion_matches_together: int


class DisputeEvidenceRead(BaseModel):
    """Evidence metadata only — never the image bytes and never the uploader's
    private data. The image itself stays behind the existing
    /matches/{id}/evidence/{eid}/image authorization."""

    id: UUID
    submitted_by: UUID
    claimed_score_a: int
    claimed_score_b: int
    has_image: bool
    created_at: datetime


DisputeDetail.model_rebuild()
