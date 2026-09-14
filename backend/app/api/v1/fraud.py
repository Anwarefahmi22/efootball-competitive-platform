from collections import Counter

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import get_current_admin
from app.db.session import get_db
from app.models.match import Match, MatchStatus
from app.models.user import User
from app.schemas.trust import CollusionCandidate

router = APIRouter()


@router.get("/collusion-candidates", response_model=list[CollusionCandidate])
async def collusion_candidates(
    min_matches: int = Query(default=3, ge=2, le=50),
    _admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> list[CollusionCandidate]:
    """Rule-based signal only: flags player pairs who have faced each other
    an unusually high number of times. This is NOT proof of collusion — it
    is a starting point for manual review.

    Nothing here writes state, penalises anyone, or feeds trust: a signal
    stays a signal until an admin makes a decision.
    """
    rows = await db.execute(
        select(Match.player_a_id, Match.player_b_id).where(
            Match.status == MatchStatus.COMPLETED,
            Match.player_a_id.isnot(None),
            Match.player_b_id.isnot(None),
        )
    )
    # Canonicalise each pair so (A,B) and (B,A) count as the same fixture.
    counts: Counter = Counter()
    for a, b in rows.all():
        counts[(a, b) if a <= b else (b, a)] += 1

    flagged = [(pair, n) for pair, n in counts.items() if n >= min_matches]
    if not flagged:
        return []
    flagged.sort(key=lambda item: (-item[1], str(item[0][0]), str(item[0][1])))

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
            matches_together=n,
        )
        for pair, n in flagged
    ]
