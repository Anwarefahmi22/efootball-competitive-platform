from uuid import UUID

from pydantic import BaseModel


class PlatformAnalytics(BaseModel):
    total_users: int
    total_tournaments: int
    total_tournaments_completed: int
    total_matches: int
    total_matches_completed: int
    total_disputes: int
    total_wallet_balance: int
    total_prize_distributed: int
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
    wallet_balance: int
    tournaments_won: int


class TournamentAnalytics(BaseModel):
    tournament_id: UUID
    name: str
    format: str
    participant_count: int
    matches_total: int
    matches_completed: int
    avg_goals_per_match: float
    entry_fee: int
    prize_pool: int
    prize_distributed: bool
