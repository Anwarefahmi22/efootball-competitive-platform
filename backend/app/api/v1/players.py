from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.v1.auth import get_current_user
from app.db.session import get_db
from app.models.rating import PlayerRating
from app.models.social import PlayerLike
from app.models.tournament import Tournament
from app.models.user import User
from app.schemas.player import PlayerCardRead

router = APIRouter()


@router.get("/cards", response_model=list[PlayerCardRead])
async def player_cards(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[PlayerCardRead]:
    """Every active player's Arena Star card, strongest first (ELO desc,
    arena number as tiebreak). Players with no documented match yet have
    no PlayerRating row — they default to the starting 1000 / zeros."""
    users_result = await db.execute(
        select(User)
        .options(selectinload(User.profile))
        .where(User.is_active.is_(True))
        .order_by(User.created_at)
    )
    users = list(users_result.scalars().all())

    ratings = {
        row.user_id: row
        for row in (await db.execute(select(PlayerRating))).scalars().all()
    }
    cups = {
        winner_id: count
        for winner_id, count in (
            await db.execute(
                select(Tournament.winner_id, func.count(Tournament.id))
                .where(Tournament.winner_id.is_not(None))
                .group_by(Tournament.winner_id)
            )
        ).all()
    }
    likes = {
        player_id: count
        for player_id, count in (
            await db.execute(
                select(PlayerLike.player_id, func.count(PlayerLike.id)).group_by(
                    PlayerLike.player_id
                )
            )
        ).all()
    }
    liked_by_me = {
        row[0]
        for row in (
            await db.execute(
                select(PlayerLike.player_id).where(PlayerLike.user_id == current_user.id)
            )
        ).all()
    }

    cards: list[PlayerCardRead] = []
    for user in users:
        rating = ratings.get(user.id)
        profile = user.profile
        cards.append(
            PlayerCardRead(
                user_id=user.id,
                arena_no=user.arena_no,
                display_name=user.display_name,
                avatar_url=profile.avatar_url if profile else None,
                country=profile.country if profile else None,
                efootball_ign=profile.efootball_ign if profile else None,
                is_verified=user.is_verified,
                rating=rating.rating if rating else 1000,
                matches_played=rating.matches_played if rating else 0,
                wins=rating.wins if rating else 0,
                cups=cups.get(user.id, 0),
                formation=profile.formation if profile else None,
                squad_strength=profile.squad_strength if profile else None,
                likes_count=likes.get(user.id, 0),
                liked_by_me=user.id in liked_by_me,
                is_me=user.id == current_user.id,
            )
        )
    cards.sort(key=lambda card: (-card.rating, card.arena_no))
    return cards


@router.post("/{user_id}/like", status_code=status.HTTP_204_NO_CONTENT)
async def like_player(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="You cannot like your own card",
        )
    target = await db.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Player not found")
    existing = await db.execute(
        select(PlayerLike).where(
            PlayerLike.player_id == user_id, PlayerLike.user_id == current_user.id
        )
    )
    if existing.scalar_one_or_none() is not None:
        return
    db.add(PlayerLike(player_id=user_id, user_id=current_user.id))
    await db.commit()


@router.delete("/{user_id}/like", status_code=status.HTTP_204_NO_CONTENT)
async def unlike_player(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    existing = await db.execute(
        select(PlayerLike).where(
            PlayerLike.player_id == user_id, PlayerLike.user_id == current_user.id
        )
    )
    like = existing.scalar_one_or_none()
    if like is not None:
        await db.delete(like)
        await db.commit()
