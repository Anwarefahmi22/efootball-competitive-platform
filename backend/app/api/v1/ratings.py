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
        losses=row.losses,
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
        .order_by(PlayerRating.rating.desc(), PlayerRating.wins.desc())
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
        user = await db.execute(select(User).where(User.id == user_id))
        if user.scalar_one_or_none() is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rating not found")
    return _to_public(rating)
