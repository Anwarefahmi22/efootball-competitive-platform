from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.models.rating import PlayerRating
from app.models.user import User
from app.schemas.rating import RatingPublic

router = APIRouter()


def _to_public(row: PlayerRating) -> RatingPublic:
    return RatingPublic(
        user_id=row.user_id,
        display_name=row.user.display_name if row.user else "",
        rating=row.rating,
        matches_played=row.matches_played,
        wins=row.wins,
        draws=row.draws,
        losses=row.losses,
        goals_for=row.goals_for,
        goals_against=row.goals_against,
        goal_difference=row.goals_for - row.goals_against,
        points=row.points,
    )


@router.get("/leaderboard", response_model=list[RatingPublic])
async def leaderboard(
    limit: int = Query(default=50, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> list[RatingPublic]:
    result = await db.execute(
        select(PlayerRating)
        .options(selectinload(PlayerRating.user))
        .order_by(
            PlayerRating.points.desc(),
            (PlayerRating.goals_for - PlayerRating.goals_against).desc(),
            PlayerRating.goals_for.desc(),
            PlayerRating.rating.desc(),
            PlayerRating.wins.desc(),
            # AUD-27: fully-tied rows need a deterministic final key,
            # or identical requests can reshuffle them.
            PlayerRating.user_id,
        )
        .limit(limit)
        .offset(offset)
    )
    return [_to_public(r) for r in result.scalars().all()]


@router.get("/{user_id}", response_model=RatingPublic)
async def get_rating(user_id: UUID, db: AsyncSession = Depends(get_db)) -> RatingPublic:
    result = await db.execute(
        select(PlayerRating)
        .options(selectinload(PlayerRating.user))
        .where(PlayerRating.user_id == user_id)
    )
    rating = result.scalar_one_or_none()
    if rating is None:
        user_result = await db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        # Rating rows are created lazily on the first completed match.
        # A registered player who has not played yet holds the initial
        # rating (model default 1000) with zeroed counters — report
        # that instead of 404ing on a valid player.
        return RatingPublic(
            user_id=user.id,
            display_name=user.display_name,
            rating=1000,
            matches_played=0,
            wins=0,
            draws=0,
            losses=0,
            goals_for=0,
            goals_against=0,
            goal_difference=0,
            points=0,
        )
    return _to_public(rating)
