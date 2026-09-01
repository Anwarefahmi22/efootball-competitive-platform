from uuid import UUID

from pydantic import BaseModel


class GroupStandingRow(BaseModel):
    user_id: UUID
    display_name: str
    played: int
    wins: int
    draws: int
    losses: int
    goals_for: int
    goals_against: int
    goal_difference: int
    points: int


class GroupRead(BaseModel):
    id: UUID
    name: str
    standings: list[GroupStandingRow]
