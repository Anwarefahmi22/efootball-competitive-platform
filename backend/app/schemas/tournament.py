from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.tournament import TournamentFormat, TournamentStatus


def _is_power_of_two(n: int) -> bool:
    return n > 0 and (n & (n - 1)) == 0


class TournamentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    format: TournamentFormat = TournamentFormat.SINGLE_ELIMINATION
    max_participants: int
    entry_fee: int = 0
    starts_at: datetime | None = None

    @field_validator("max_participants")
    @classmethod
    def validate_max_participants(cls, value: int) -> int:
        if value < 4 or value > 64 or not _is_power_of_two(value):
            raise ValueError("max_participants must be a power of 2 between 4 and 64")
        return value

    @field_validator("format")
    @classmethod
    def validate_format(cls, value: TournamentFormat) -> TournamentFormat:
        if value != TournamentFormat.SINGLE_ELIMINATION:
            raise ValueError("Only single_elimination is supported in this phase")
        return value


class ParticipantPublic(BaseModel):
    user_id: UUID
    display_name: str
    seed: int | None


class TournamentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    format: TournamentFormat
    status: TournamentStatus
    max_participants: int
    entry_fee: int
    prize_pool: int
    created_by: UUID
    starts_at: datetime | None
    created_at: datetime
    updated_at: datetime
    participant_count: int = 0
    participants: list[ParticipantPublic] = []
