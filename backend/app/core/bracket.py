from __future__ import annotations

import math
import random
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.match import Match, MatchStatus
from app.models.tournament import Tournament, TournamentParticipant, TournamentStatus


def is_power_of_two(n: int) -> bool:
    return n >= 2 and (n & (n - 1)) == 0


def num_rounds(participant_count: int) -> int:
    return int(math.log2(participant_count))


def next_match_placement(round_slot: int) -> tuple[int, str]:
    next_slot = round_slot // 2
    side = "a" if round_slot % 2 == 0 else "b"
    return next_slot, side


def assign_random_seeds(participants: list[TournamentParticipant]) -> None:
    """The draw: randomly assigns seed numbers 1..n. Does NOT create matches —
    that happens separately when the tournament is started, using this order."""
    shuffled = list(participants)
    random.shuffle(shuffled)
    for seed, participant in enumerate(shuffled, start=1):
        participant.seed = seed


async def build_bracket_matches(
    db: AsyncSession,
    tournament: Tournament,
    participants: list[TournamentParticipant],
) -> None:
    """Creates matches from ALREADY-SEEDED participants (via assign_random_seeds
    during the draw step). Does not re-shuffle — the draw is final."""
    n = len(participants)
    if not is_power_of_two(n):
        raise ValueError("Participant count must be a power of 2")

    by_seed = sorted(participants, key=lambda p: p.seed or 0)
    rounds = num_rounds(n)

    round_one_count = n // 2
    for i in range(round_one_count):
        player_a = by_seed[i * 2]
        player_b = by_seed[i * 2 + 1]
        db.add(
            Match(
                tournament_id=tournament.id,
                round_number=1,
                bracket_slot=i,
                player_a_id=player_a.user_id,
                player_b_id=player_b.user_id,
                status=MatchStatus.READY,
            )
        )

    for round_number in range(2, rounds + 1):
        match_count = n // (2**round_number)
        for slot in range(match_count):
            db.add(
                Match(
                    tournament_id=tournament.id,
                    round_number=round_number,
                    bracket_slot=slot,
                    player_a_id=None,
                    player_b_id=None,
                    status=MatchStatus.WAITING,
                )
            )

    tournament.status = TournamentStatus.IN_PROGRESS


async def matches_in_round(
    db: AsyncSession, tournament_id: UUID, round_number: int
) -> list[Match]:
    # CRITICAL: group_id.is_(None) restricts this to knockout-stage matches
    # only. Group-stage matches reuse round_number 1..N for their own
    # internal round-robin schedule, and without this filter a knockout
    # winner could be silently advanced into a leftover group-stage match
    # instead of the real next knockout round.
    result = await db.execute(
        select(Match)
        .where(
            Match.tournament_id == tournament_id,
            Match.round_number == round_number,
            Match.group_id.is_(None),
        )
        .order_by(Match.bracket_slot)
    )
    return list(result.scalars().all())


async def advance_winner(db: AsyncSession, match: Match, winner_id: UUID) -> None:
    if winner_id is None:
        # Nothing to advance. Writing None into a destination slot would clear
        # a player who had already legitimately qualified for that match.
        return

    tournament_result = await db.execute(
        select(Tournament)
        .options(selectinload(Tournament.participants))
        .where(Tournament.id == match.tournament_id)
    )
    tournament = tournament_result.scalar_one()

    slot = match.bracket_slot

    next_round_matches = await matches_in_round(
        db, match.tournament_id, match.round_number + 1
    )
    if not next_round_matches:
        if tournament.status == TournamentStatus.CANCELLED:
            # Never resurrect a tournament that has been called off.
            return
        tournament.status = TournamentStatus.COMPLETED
        tournament.winner_id = winner_id
        return

    next_slot, side = next_match_placement(slot)
    if next_slot >= len(next_round_matches):
        raise ValueError("No destination match for winner")

    dest = next_round_matches[next_slot]
    # Advancement must be idempotent and must never displace someone. Each
    # bracket slot maps to exactly one destination side, so an already-filled
    # side holding a *different* player means something went wrong upstream —
    # fail loudly rather than silently rewriting a match that may already be
    # under way.
    occupied = dest.player_a_id if side == "a" else dest.player_b_id
    if occupied is None:
        if side == "a":
            dest.player_a_id = winner_id
        else:
            dest.player_b_id = winner_id
    elif occupied != winner_id:
        raise ValueError("Destination match already holds a different winner")

    if dest.player_a_id is not None and dest.player_b_id is not None:
        dest.status = MatchStatus.READY
