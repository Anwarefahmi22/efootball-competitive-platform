from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_user
from app.core.bracket import advance_winner
from app.core.rating import new_rating
from app.db.session import get_db
from app.models.match import Match, MatchStatus
from app.models.rating import PlayerRating
from app.models.user import User
from app.schemas.match import MatchRead, SubmitResult

router = APIRouter()
tournament_matches_router = APIRouter()


async def _get_or_create_rating(db: AsyncSession, user_id: UUID) -> PlayerRating:
    result = await db.execute(select(PlayerRating).where(PlayerRating.user_id == user_id))
    rating = result.scalar_one_or_none()
    if rating is None:
        rating = PlayerRating(user_id=user_id, rating=1000)
        db.add(rating)
        await db.flush()
    return rating


async def _apply_elo(db: AsyncSession, winner_id: UUID, loser_id: UUID) -> None:
    winner = await _get_or_create_rating(db, winner_id)
    loser = await _get_or_create_rating(db, loser_id)
    winner_new = new_rating(winner.rating, loser.rating, 1.0)
    loser_new = new_rating(loser.rating, winner.rating, 0.0)
    winner.rating = winner_new
    loser.rating = loser_new
    winner.matches_played += 1
    loser.matches_played += 1
    winner.wins += 1
    loser.losses += 1


@router.get("/{match_id}", response_model=MatchRead)
async def get_match(match_id: UUID, db: AsyncSession = Depends(get_db)) -> Match:
    result = await db.execute(select(Match).where(Match.id == match_id))
    match = result.scalar_one_or_none()
    if match is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found")
    return match


@tournament_matches_router.get("/{tournament_id}/matches", response_model=list[MatchRead])
async def list_tournament_matches(
    tournament_id: UUID, db: AsyncSession = Depends(get_db)
) -> list[Match]:
    result = await db.execute(
        select(Match)
        .where(Match.tournament_id == tournament_id)
        .order_by(Match.round_number, Match.bracket_slot)
    )
    return list(result.scalars().all())


@router.post("/{match_id}/submit-result", response_model=MatchRead)
async def submit_result(
    match_id: UUID,
    payload: SubmitResult,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Match:
    result = await db.execute(select(Match).where(Match.id == match_id))
    match = result.scalar_one_or_none()
    if match is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found")

    if current_user.id not in {match.player_a_id, match.player_b_id}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only match participants can submit a result",
        )
    if match.status not in {MatchStatus.READY, MatchStatus.IN_PROGRESS}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Match is not accepting results",
        )
    if match.player_a_id is None or match.player_b_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Match does not have two players"
        )
    if payload.score_a == payload.score_b:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Draws are not allowed"
        )

    winner_id = match.player_a_id if payload.score_a > payload.score_b else match.player_b_id
    loser_id = match.player_b_id if winner_id == match.player_a_id else match.player_a_id

    match.score_a = payload.score_a
    match.score_b = payload.score_b
    match.winner_id = winner_id
    match.status = MatchStatus.COMPLETED
    match.completed_at = datetime.now(timezone.utc)

    await _apply_elo(db, winner_id, loser_id)
    await advance_winner(db, match, winner_id)
    await db.commit()
    await db.refresh(match)
    return match
