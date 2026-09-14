from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.match import MatchStatus


class MatchRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tournament_id: UUID
    round_number: int
    # bracket_slot is the 0-indexed position of the match within its round. It
    # drives bracket ordering and winner advancement (core/bracket.py) and is
    # NOT NULL in the DB, so clients need it to render the bracket correctly —
    # created_at/id ordering is unreliable for same-transaction matches.
    bracket_slot: int
    # group_id is NULL for knockout/league matches and set for group-stage
    # matches. group_knockout reuses round_number 1..N in every group, so this
    # is the only way a client can tell the two stages apart.
    group_id: UUID | None = None
    player_a_id: UUID | None
    player_b_id: UUID | None
    status: MatchStatus
    score_a: int | None
    score_b: int | None
    winner_id: UUID | None
    scheduled_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class SubmitResult(BaseModel):
    score_a: int = Field(ge=0)
    score_b: int = Field(ge=0)
