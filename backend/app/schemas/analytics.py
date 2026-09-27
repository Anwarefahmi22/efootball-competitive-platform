from uuid import UUID

from pydantic import BaseModel


# HF-1: platform analytics are competitive/integrity metrics only — no
# financial totals.
class PlatformAnalytics(BaseModel):
    total_users: int
    total_tournaments: int
    total_tournaments_completed: int
    total_matches: int
    total_matches_completed: int
    total_disputes: int
    total_disputes_open: int
    total_disputes_resolved: int
    total_posts: int


class PlayerAnalytics(BaseModel):
    user_id: UUID
    display_name: str
    rating: int
    matches_played: int
    wins: int
    losses: int
    win_rate: float
    avg_goals_scored: float
    avg_goals_conceded: float
    trust_score: int
    tournaments_won: int


class TournamentAnalytics(BaseModel):
    tournament_id: UUID
    name: str
    format: str
    participant_count: int
    matches_total: int
    matches_completed: int
    avg_goals_per_match: float
