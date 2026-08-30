from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.match import MatchStatus


class MatchRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tournament_id: UUID
    round_number: int
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
