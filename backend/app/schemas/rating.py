from uuid import UUID

from pydantic import BaseModel


class RatingPublic(BaseModel):
    user_id: UUID
    display_name: str
    rating: int
    matches_played: int
    wins: int
    draws: int
    losses: int
    goals_for: int
    goals_against: int
    goal_difference: int
    points: int
