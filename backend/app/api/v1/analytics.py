from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.analytics import get_platform_analytics, get_player_analytics, get_tournament_analytics
from app.api.v1.auth import get_current_user
from app.core.permissions import get_current_admin, is_admin
from app.db.session import get_db
from app.models.user import User
from app.schemas.analytics import PlatformAnalytics, PlayerAnalytics, TournamentAnalytics

router = APIRouter()


@router.get("/platform", response_model=PlatformAnalytics)
async def platform_analytics(
    _admin: User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)
) -> PlatformAnalytics:
    data = await get_platform_analytics(db)
    return PlatformAnalytics(**data)


@router.get("/players/{user_id}", response_model=PlayerAnalytics)
async def player_analytics(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PlayerAnalytics:
    data = await get_player_analytics(db, user_id)
    if data is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    # SECURITY: wallet_balance is financial data — only the account owner or
    # a platform admin may see it. Everyone else gets it hidden (None).
    if current_user.id != user_id and not await is_admin(db, current_user.id):
        data["wallet_balance"] = None
    return PlayerAnalytics(**data)


@router.get("/tournaments/{tournament_id}", response_model=TournamentAnalytics)
async def tournament_analytics(tournament_id: UUID, db: AsyncSession = Depends(get_db)) -> TournamentAnalytics:
    data = await get_tournament_analytics(db, tournament_id)
    if data is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tournament not found")
    return TournamentAnalytics(**data)
