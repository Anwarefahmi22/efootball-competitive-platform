from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.match import Match, MatchStatus
from app.models.tournament import Tournament, TournamentParticipant
from app.models.user import User


async def compute_season_standings(db: AsyncSession, season_id: UUID) -> list[dict]:
    """Season points: 3 for winning a match, 1 for a draw (league matches),
    0 for a loss — aggregated across every tournament tagged to this season."""
    tournaments_result = await db.execute(select(Tournament).where(Tournament.season_id == season_id))
    tournament_ids = [t.id for t in tournaments_result.scalars().all()]
    if not tournament_ids:
        return []

    stats: dict[UUID, dict] = {}

    for tid in tournament_ids:
        participants_result = await db.execute(
            select(TournamentParticipant).where(TournamentParticipant.tournament_id == tid)
        )
        for p in participants_result.scalars().all():
            stats.setdefault(
                p.user_id,
                {"tournaments": set(), "played": 0, "wins": 0, "losses": 0, "points": 0},
            )
            stats[p.user_id]["tournaments"].add(tid)

        matches_result = await db.execute(
            select(Match).where(Match.tournament_id == tid, Match.status == MatchStatus.COMPLETED)
        )
        for m in matches_result.scalars().all():
            if m.player_a_id not in stats or m.player_b_id not in stats:
                continue
            a, b = stats[m.player_a_id], stats[m.player_b_id]
            a["played"] += 1
            b["played"] += 1
            if m.score_a == m.score_b:
                a["points"] += 1
                b["points"] += 1
            elif m.score_a > m.score_b:
                a["wins"] += 1
                b["losses"] += 1
                a["points"] += 3
            else:
                b["wins"] += 1
                a["losses"] += 1
                b["points"] += 3

    rows = []
    for user_id, s in stats.items():
        user_result = await db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
        rows.append({
            "user_id": user_id,
            "display_name": user.display_name if user else "",
            "tournaments_played": len(s["tournaments"]),
            "matches_played": s["played"],
            "wins": s["wins"],
            "losses": s["losses"],
            "points": s["points"],
        })

    # Trailing key only makes the order of fully-tied rows deterministic; it
    # does not change the points/wins ranking policy.
    rows.sort(key=lambda r: (-r["points"], -r["wins"], str(r["user_id"])))
    return rows
