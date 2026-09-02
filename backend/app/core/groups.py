from __future__ import annotations

import string
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.league import build_round_robin_schedule
from app.models.group import Group
from app.models.match import Match, MatchStatus
from app.models.rating import PlayerRating
from app.models.tournament import Tournament, TournamentParticipant
from app.models.user import User


def is_valid_group_count(num_groups: int) -> bool:
    return num_groups >= 2 and (num_groups & (num_groups - 1)) == 0


async def assign_seeded_groups(
    db: AsyncSession, tournament: Tournament, participants: list[TournamentParticipant], num_groups: int
) -> list[Group]:
    """Snake-draft distribution by ELO rating, like World Cup pots: the
    strongest players are spread across different groups first."""
    ratings: dict[UUID, int] = {}
    for p in participants:
        result = await db.execute(select(PlayerRating).where(PlayerRating.user_id == p.user_id))
        rating = result.scalar_one_or_none()
        ratings[p.user_id] = rating.rating if rating else 1000

    ordered = sorted(participants, key=lambda p: ratings[p.user_id], reverse=True)

    letters = string.ascii_uppercase
    groups = [Group(tournament_id=tournament.id, name=letters[i]) for i in range(num_groups)]
    for g in groups:
        db.add(g)
    await db.flush()

    buckets: list[list[TournamentParticipant]] = [[] for _ in range(num_groups)]
    forward = True
    i = 0
    while i < len(ordered):
        group_range = range(num_groups) if forward else range(num_groups - 1, -1, -1)
        for gi in group_range:
            if i >= len(ordered):
                break
            buckets[gi].append(ordered[i])
            i += 1
        forward = not forward

    for group, members in zip(groups, buckets):
        for p in members:
            p.group_id = group.id

    return groups


async def generate_group_matches(db: AsyncSession, tournament: Tournament, groups: list[Group]) -> None:
    for group in groups:
        result = await db.execute(
            select(TournamentParticipant).where(TournamentParticipant.group_id == group.id)
        )
        members = list(result.scalars().all())
        schedule = build_round_robin_schedule([m.user_id for m in members])
        for round_index, pairs in enumerate(schedule, start=1):
            for slot_index, (a, b) in enumerate(pairs):
                db.add(
                    Match(
                        tournament_id=tournament.id,
                        group_id=group.id,
                        round_number=round_index,
                        bracket_slot=slot_index,
                        player_a_id=a,
                        player_b_id=b,
                        status=MatchStatus.READY,
                    )
                )


async def compute_group_standings(db: AsyncSession, group_id: UUID) -> list[dict]:
    participants_result = await db.execute(
        select(TournamentParticipant).where(TournamentParticipant.group_id == group_id)
    )
    participants = list(participants_result.scalars().all())

    stats: dict[UUID, dict] = {
        p.user_id: {
            "played": 0, "wins": 0, "draws": 0, "losses": 0,
            "goals_for": 0, "goals_against": 0, "points": 0,
        }
        for p in participants
    }

    matches_result = await db.execute(
        select(Match).where(Match.group_id == group_id, Match.status == MatchStatus.COMPLETED)
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
        user_result = await db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
        rows.append({
            "user_id": user_id,
            "display_name": user.display_name if user else "",
            "goal_difference": s["goals_for"] - s["goals_against"],
            **s,
        })

    rows.sort(key=lambda r: (-r["points"], -r["goal_difference"], -r["goals_for"]))
    rows = await _apply_head_to_head_tiebreak(db, group_id, rows)
    return rows


async def _apply_head_to_head_tiebreak(db: AsyncSession, group_id: UUID, rows: list[dict]) -> list[dict]:
    """When two or more players are tied on points after the primary sort,
    re-order that tied cluster using a mini head-to-head table computed only
    from matches played among the tied players themselves — same approach
    FIFA uses for World Cup group stage tiebreaks."""
    if len(rows) < 2:
        return rows

    matches_result = await db.execute(
        select(Match).where(Match.group_id == group_id, Match.status == MatchStatus.COMPLETED)
    )
    all_matches = list(matches_result.scalars().all())

    result: list[dict] = []
    i = 0
    while i < len(rows):
        j = i + 1
        while j < len(rows) and rows[j]["points"] == rows[i]["points"]:
            j += 1
        cluster = rows[i:j]
        if len(cluster) == 1:
            result.append(cluster[0])
        else:
            tied_ids = {r["user_id"] for r in cluster}
            h2h_stats = {
                r["user_id"]: {"points": 0, "goal_difference": 0, "goals_for": 0} for r in cluster
            }
            for m in all_matches:
                if m.player_a_id in tied_ids and m.player_b_id in tied_ids:
                    a, b = h2h_stats[m.player_a_id], h2h_stats[m.player_b_id]
                    a["goals_for"] += m.score_a
                    a["goal_difference"] += m.score_a - m.score_b
                    b["goals_for"] += m.score_b
                    b["goal_difference"] += m.score_b - m.score_a
                    if m.score_a == m.score_b:
                        a["points"] += 1
                        b["points"] += 1
                    elif m.score_a > m.score_b:
                        a["points"] += 3
                    else:
                        b["points"] += 3
            cluster_sorted = sorted(
                cluster,
                key=lambda r: (
                    -h2h_stats[r["user_id"]]["points"],
                    -h2h_stats[r["user_id"]]["goal_difference"],
                    -h2h_stats[r["user_id"]]["goals_for"],
                ),
            )
            result.extend(cluster_sorted)
        i = j
    return result


async def is_group_stage_complete(db: AsyncSession, tournament_id: UUID) -> bool:
    result = await db.execute(
        select(Match).where(
            Match.tournament_id == tournament_id,
            Match.group_id.isnot(None),
            Match.status.notin_([MatchStatus.COMPLETED, MatchStatus.CANCELLED]),
        )
    )
    return result.scalars().first() is None


async def get_qualifiers(db: AsyncSession, tournament_id: UUID) -> list[UUID]:
    """Top 2 from each group, ordered group A-1st, B-1st, C-1st... then
    A-2nd, B-2nd... — standard World-Cup-style bracket seeding."""
    groups_result = await db.execute(
        select(Group).where(Group.tournament_id == tournament_id).order_by(Group.name)
    )
    groups = list(groups_result.scalars().all())

    firsts: list[UUID] = []
    seconds: list[UUID] = []
    for group in groups:
        standings = await compute_group_standings(db, group.id)
        if len(standings) >= 2:
            firsts.append(standings[0]["user_id"])
            seconds.append(standings[1]["user_id"])

    return firsts + seconds
