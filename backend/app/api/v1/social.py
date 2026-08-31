from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_user
from app.db.session import get_db
from app.models.social import Follow
from app.models.user import User
from app.schemas.social import FollowStats

router = APIRouter()


@router.post("/{user_id}/follow", status_code=status.HTTP_204_NO_CONTENT)
async def follow_user(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    if user_id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot follow yourself")
    target = await db.execute(select(User).where(User.id == user_id))
    if target.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    existing = await db.execute(
        select(Follow).where(Follow.follower_id == current_user.id, Follow.followed_id == user_id)
    )
    if existing.scalar_one_or_none() is not None:
        return
    db.add(Follow(follower_id=current_user.id, followed_id=user_id))
    await db.commit()


@router.delete("/{user_id}/follow", status_code=status.HTTP_204_NO_CONTENT)
async def unfollow_user(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    existing = await db.execute(
        select(Follow).where(Follow.follower_id == current_user.id, Follow.followed_id == user_id)
    )
    follow = existing.scalar_one_or_none()
    if follow is not None:
        await db.delete(follow)
        await db.commit()


@router.get("/{user_id}/follow-stats", response_model=FollowStats)
async def follow_stats(
    user_id: UUID,
    current_user: User | None = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FollowStats:
    followers_count = await db.execute(
        select(func.count()).select_from(Follow).where(Follow.followed_id == user_id)
    )
    following_count = await db.execute(
        select(func.count()).select_from(Follow).where(Follow.follower_id == user_id)
    )
    is_following = False
    if current_user is not None:
        existing = await db.execute(
            select(Follow).where(
                Follow.follower_id == current_user.id, Follow.followed_id == user_id
            )
        )
        is_following = existing.scalar_one_or_none() is not None
    return FollowStats(
        user_id=user_id,
        followers_count=followers_count.scalar_one(),
        following_count=following_count.scalar_one(),
        is_following=is_following,
    )
