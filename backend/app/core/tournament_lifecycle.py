import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import AsyncSessionLocal
from app.models.match import Match
from app.models.tournament import Tournament, TournamentStatus

logger = logging.getLogger(__name__)

INACTIVITY_LIMIT = timedelta(days=3)
MAINTENANCE_INTERVAL = timedelta(hours=1)


async def cancel_inactive_tournaments() -> int:
    """Cancel in-progress tournaments with no tournament or match activity for 3 days."""
    now = datetime.now(timezone.utc)
    cutoff = now - INACTIVITY_LIMIT
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Tournament, func.max(Match.updated_at).label("last_match_activity"))
            .outerjoin(Match, Match.tournament_id == Tournament.id)
            .where(Tournament.status == TournamentStatus.IN_PROGRESS)
            .group_by(Tournament.id)
        )
        expired = []
        for tournament, last_match_activity in result.all():
            last_activity = max(
                tournament.updated_at,
                last_match_activity or tournament.created_at,
            )
            if last_activity <= cutoff:
                tournament.status = TournamentStatus.CANCELLED
                expired.append(tournament.id)
        if expired:
            await db.commit()
            logger.info("Cancelled %d inactive tournaments", len(expired))
        return len(expired)


async def tournament_maintenance_loop() -> None:
    while True:
        try:
            await cancel_inactive_tournaments()
        except SQLAlchemyError:
            logger.exception("Tournament inactivity maintenance failed")
        await asyncio.sleep(MAINTENANCE_INTERVAL.total_seconds())
