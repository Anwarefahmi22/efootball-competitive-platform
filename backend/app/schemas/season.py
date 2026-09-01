from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.models.season import SeasonStatus


class SeasonCreate(BaseModel):
    name: str
    starts_at: datetime
    ends_at: datetime


class SeasonRead(BaseModel):
    id: UUID
    name: str
    status: SeasonStatus
    starts_at: datetime
    ends_at: datetime
    created_at: datetime


class SeasonStandingRow(BaseModel):
    user_id: UUID
    display_name: str
    tournaments_played: int
    matches_played: int
    wins: int
    losses: int
    points: int
