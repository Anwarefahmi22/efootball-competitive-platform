from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.match import Match, MatchStatus
from app.models.tournament import Tournament, TournamentParticipant
from app.models.user import Profile, User


def build_round_robin_schedule(player_ids: list[UUID]) -> list[list[tuple[UUID, UUID]]]:
    """Standard circle-method round-robin. Returns a list of rounds, each a
    list of (player_a, player_b) pairs. Handles odd counts via a bye slot."""
    players: list[UUID | None] = list(player_ids)
    if len(players) % 2 == 1:
        players.append(None)

    n = len(players)
    rounds: list[list[tuple[UUID, UUID]]] = []
    for _ in range(n - 1):
        pairs = []
        for i in range(n // 2):
            a, b = players[i], players[n - 1 - i]
            if a is not None and b is not None:
                pairs.append((a, b))
        rounds.append(pairs)
        players.insert(1, players.pop())
    return rounds


async def generate_league_schedule(
    db: AsyncSession, tournament: Tournament, participants: list[TournamentParticipant]
) -> None:
    schedule = build_round_robin_schedule([p.user_id for p in participants])
    for round_index, pairs in enumerate(schedule, start=1):
        for slot_index, (player_a, player_b) in enumerate(pairs):
            db.add(
                Match(
                    tournament_id=tournament.id,
                    round_number=round_index,
                    bracket_slot=slot_index,
                    player_a_id=player_a,
                    player_b_id=player_b,
                    status=MatchStatus.READY,
                )
            )


async def compute_standings(db: AsyncSession, tournament_id: UUID) -> list[dict]:
    tournament_result = await db.execute(
        select(Tournament)
        .options(selectinload(Tournament.participants))
        .where(Tournament.id == tournament_id)
    )
    tournament = tournament_result.scalar_one()

    stats: dict[UUID, dict] = {
        p.user_id: {
            "played": 0, "wins": 0, "draws": 0, "losses": 0,
            "goals_for": 0, "goals_against": 0, "points": 0,
        }
        for p in tournament.participants
    }

    matches_result = await db.execute(
        select(Match).where(
            Match.tournament_id == tournament_id, Match.status == MatchStatus.COMPLETED
        )
    )
    for m in matches_result.scalars().all():
        if m.player_a_id not in stats or m.player_b_id not in stats:
            continue
        a, b = stats[m.player_a_id], stats[m.player_b_id]
        a["played"] += 1
        b["played"] += 1
        a["goals_for"] += m.score_a
        a["goals_against"] += m.score_b
        b["goals_for"] += m.score_b
        b["goals_against"] += m.score_a
        if m.score_a == m.score_b:
            a["draws"] += 1
            b["draws"] += 1
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
        user_result = await db.execute(
            select(User, Profile).outerjoin(Profile, Profile.user_id == User.id).where(User.id == user_id)
        )
        row = user_result.first()
        user, profile = row if row else (None, None)
        rows.append({
            "user_id": user_id,
            "display_name": user.display_name if user else "",
            "avatar_url": profile.avatar_url if profile else None,
            "goal_difference": s["goals_for"] - s["goals_against"],
            **s,
        })

    rows.sort(key=lambda r: (-r["points"], -r["goal_difference"], -r["goals_for"]))
    return rows


async def is_league_complete(db: AsyncSession, tournament_id: UUID) -> bool:
    result = await db.execute(
        select(Match).where(
            Match.tournament_id == tournament_id,
            Match.status.notin_([MatchStatus.COMPLETED, MatchStatus.CANCELLED]),
        )
    )
    return result.scalars().first() is None
