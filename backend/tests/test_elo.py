"""AUD-01: pure ELO unit tests (app.core.rating).

Expected values are the standard Elo expectation with K=32, computed
independently of the implementation:
  expected_a = 1 / (1 + 10 ** ((rb - ra) / 400)); delta = round(32 * (score - expected)).
"""
import pytest

from app.core.rating import new_rating, new_rating_draw

CASES = [
    # (rating_a, rating_b, score_a, expected_a_after, expected_b_after)
    (1000, 1000, 1.0, 1016, 984),   # equal ratings, A wins
    (1000, 1000, 0.0, 984, 1016),   # equal ratings, A loses
    (1200, 1000, 1.0, 1208, 992),   # favourite wins: small gain
    (1000, 1200, 1.0, 1024, 1176),  # upset win: large gain
    (1200, 1000, 0.0, 1176, 1024),  # favourite loses: large drop
]


@pytest.mark.parametrize("ra,rb,score,exp_a,exp_b", CASES)
def test_new_rating_known_values(ra, rb, score, exp_a, exp_b):
    assert new_rating(ra, rb, score) == exp_a
    assert new_rating(rb, ra, 1.0 - score) == exp_b


@pytest.mark.parametrize("ra,rb", [(1000, 1000), (1200, 1000), (800, 1500), (1016, 984)])
def test_new_rating_is_zero_sum(ra, rb):
    assert new_rating(ra, rb, 1.0) + new_rating(rb, ra, 0.0) == ra + rb


def test_draw_equal_ratings_is_neutral():
    assert new_rating_draw(1000, 1000) == 1000


def test_draw_pulls_ratings_together():
    # The higher-rated player sheds points on a draw; the lower gains.
    assert new_rating_draw(1200, 1000) < 1200
    assert new_rating_draw(1000, 1200) > 1000
    assert new_rating_draw(1200, 1000) + new_rating_draw(1000, 1200) == 2200
