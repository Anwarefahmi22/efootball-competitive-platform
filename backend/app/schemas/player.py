from uuid import UUID

from pydantic import BaseModel


class PlayerCardRead(BaseModel):
    """One Arena Star card: official competitive stats + profile data,
    aggregated for the fan-deck page in a single payload."""

    user_id: UUID
    arena_no: int
    display_name: str
    avatar_url: str | None
    country: str | None
    efootball_ign: str | None
    is_verified: bool
    rating: int
    matches_played: int
    wins: int
    cups: int
    formation: str | None
    squad_strength: int | None
    squad_image_url: str | None
    likes_count: int
    liked_by_me: bool
    is_me: bool
