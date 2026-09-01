K_FACTOR = 32


def expected_score(player_rating: int, opponent_rating: int) -> float:
    return 1 / (1 + 10 ** ((opponent_rating - player_rating) / 400))


def new_rating(player_rating: int, opponent_rating: int, actual_score: float) -> int:
    """actual_score is 1.0 for a win, 0.0 for a loss."""
    expected = expected_score(player_rating, opponent_rating)
    return round(player_rating + K_FACTOR * (actual_score - expected))


def new_rating_draw(player_rating: int, opponent_rating: int) -> int:
    """Both players get actual_score = 0.5 (draw)."""
    return new_rating(player_rating, opponent_rating, 0.5)
