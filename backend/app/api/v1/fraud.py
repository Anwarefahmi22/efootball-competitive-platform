from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import get_current_admin
from app.db.session import get_db
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
    is a starting point for manual review."""
    query = text(
        """
        SELECT
            LEAST(m.player_a_id, m.player_b_id) AS pa,
            GREATEST(m.player_a_id, m.player_b_id) AS pb,
            COUNT(*) AS matches_together
        FROM matches m
        WHERE m.player_a_id IS NOT NULL AND m.player_b_id IS NOT NULL
          AND m.status = 'completed'
        GROUP BY pa, pb
        HAVING COUNT(*) >= :min_matches
        ORDER BY matches_together DESC
        """
    )
    result = await db.execute(query, {"min_matches": min_matches})
    rows = result.all()

    if not rows:
        return []

    user_ids = {row.pa for row in rows} | {row.pb for row in rows}
    names_result = await db.execute(
        text("SELECT id, display_name FROM users WHERE id = ANY(:ids)"),
        {"ids": list(user_ids)},
    )
    names = {row.id: row.display_name for row in names_result.all()}

    return [
        CollusionCandidate(
            player_a_id=row.pa,
            player_a_name=names.get(row.pa, ""),
            player_b_id=row.pb,
            player_b_name=names.get(row.pb, ""),
            matches_together=row.matches_together,
        )
        for row in rows
    ]
