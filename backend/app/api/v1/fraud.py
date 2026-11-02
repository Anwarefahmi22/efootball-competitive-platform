from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import get_current_admin
from app.db.session import get_db
from app.models.invite import ChallengeMatch, ChallengeStatus
from app.models.match import Match, MatchStatus
from app.models.user import User
from app.schemas.trust import CollusionCandidate

router = APIRouter()


class _PairStats:
    __slots__ = ("total", "challenges", "a_wins", "b_wins", "draws")

    def __init__(self) -> None:
        self.total = 0
        self.challenges = 0
        self.a_wins = 0
        self.b_wins = 0
        self.draws = 0


@router.get("/collusion-candidates", response_model=list[CollusionCandidate])
async def collusion_candidates(
    min_matches: int = Query(default=3, ge=2, le=50),
    _admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> list[CollusionCandidate]:
    """Rule-based signal only: flags player pairs who have faced each other
    an unusually high number of times. This is NOT proof of collusion — it
    is a starting point for manual review.

    AUD-28: the scan now covers BOTH competitive surfaces — tournament
    matches and the ELO challenge matches added later (the surface a
    farming pair would actually use) — and reports the win split, so a
    one-sided pattern is visible without opening every match. Nothing
    here writes state, penalises anyone, or feeds trust: a signal stays
    a signal until an admin makes a decision.
    """
    stats: dict[tuple, _PairStats] = {}

    def record(a, b, winner_id, *, is_challenge: bool) -> None:
        if a is None or b is None:
            return
        pair = (a, b) if a <= b else (b, a)
        entry = stats.setdefault(pair, _PairStats())
        entry.total += 1
        if is_challenge:
            entry.challenges += 1
        if winner_id is None:
            entry.draws += 1
        elif winner_id == pair[0]:
            entry.a_wins += 1
        else:
            entry.b_wins += 1

    rows = await db.execute(
        select(Match.player_a_id, Match.player_b_id, Match.winner_id).where(
            Match.status == MatchStatus.COMPLETED,
            Match.player_a_id.isnot(None),
            Match.player_b_id.isnot(None),
        )
    )
    for a, b, winner in rows.all():
        record(a, b, winner, is_challenge=False)

    rows = await db.execute(
        select(
            ChallengeMatch.player_a_id,
            ChallengeMatch.player_b_id,
            ChallengeMatch.winner_id,
        ).where(ChallengeMatch.status == ChallengeStatus.COMPLETED)
    )
    for a, b, winner in rows.all():
        record(a, b, winner, is_challenge=True)

    flagged = [(pair, s) for pair, s in stats.items() if s.total >= min_matches]
    if not flagged:
        return []
    flagged.sort(key=lambda item: (-item[1].total, str(item[0][0]), str(item[0][1])))

    user_ids = {uid for pair, _ in flagged for uid in pair}
    names_result = await db.execute(
        select(User.id, User.display_name).where(User.id.in_(user_ids))
    )
    names = {row.id: row.display_name for row in names_result.all()}

    return [
        CollusionCandidate(
            player_a_id=pair[0],
            player_a_name=names.get(pair[0], ""),
            player_b_id=pair[1],
            player_b_name=names.get(pair[1], ""),
            matches_together=s.total,
            challenges_together=s.challenges,
            a_wins=s.a_wins,
            b_wins=s.b_wins,
            draws=s.draws,
        )
        for pair, s in flagged
    ]
