from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.tournament import TournamentFormat, TournamentStatus


def _is_power_of_two(n: int) -> bool:
    return n > 0 and (n & (n - 1)) == 0


class TournamentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    format: TournamentFormat = TournamentFormat.SINGLE_ELIMINATION
    max_participants: int
    entry_fee: int = 0
    season_id: UUID | None = None
    starts_at: datetime | None = None

    @model_validator(mode="after")
    def validate_participants_for_format(self) -> "TournamentCreate":
        if self.format == TournamentFormat.SINGLE_ELIMINATION:
            if self.max_participants < 4 or self.max_participants > 64 or not _is_power_of_two(self.max_participants):
                raise ValueError(
                    "max_participants must be a power of 2 between 4 and 64 for single_elimination"
                )
        elif self.format == TournamentFormat.LEAGUE:
            if self.max_participants < 2 or self.max_participants > 64:
                raise ValueError("max_participants must be between 2 and 64 for league")
        return self


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
    draw_completed: bool
    season_id: UUID | None
    created_by: UUID
    starts_at: datetime | None
    created_at: datetime
    updated_at: datetime
    participant_count: int = 0
    participants: list[ParticipantPublic] = []
