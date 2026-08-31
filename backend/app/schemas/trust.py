from uuid import UUID

from pydantic import BaseModel


class TrustPublic(BaseModel):
    user_id: UUID
    display_name: str
    trust_score: int
    verified_matches: int
    disputes_involved: int


class CollusionCandidate(BaseModel):
    player_a_id: UUID
    player_a_name: str
    player_b_id: UUID
    player_b_name: str
    matches_together: int
