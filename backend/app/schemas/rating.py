from uuid import UUID

from pydantic import BaseModel


class RatingPublic(BaseModel):
    user_id: UUID
    display_name: str
    rating: int
    matches_played: int
    wins: int
    losses: int
