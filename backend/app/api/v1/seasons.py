from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import get_current_admin
from app.core.season import compute_season_standings
from app.db.session import get_db
from app.models.season import Season
from app.models.user import User
from app.schemas.season import SeasonCreate, SeasonRead, SeasonStandingRow

router = APIRouter()


@router.post("", response_model=SeasonRead, status_code=status.HTTP_201_CREATED)
async def create_season(
    payload: SeasonCreate,
    _admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> Season:
    season = Season(name=payload.name, starts_at=payload.starts_at, ends_at=payload.ends_at)
    db.add(season)
    await db.commit()
    await db.refresh(season)
    return season


@router.get("", response_model=list[SeasonRead])
async def list_seasons(db: AsyncSession = Depends(get_db)) -> list[Season]:
    result = await db.execute(select(Season).order_by(Season.starts_at.desc()))
    return list(result.scalars().all())


@router.get("/{season_id}", response_model=SeasonRead)
async def get_season(season_id: UUID, db: AsyncSession = Depends(get_db)) -> Season:
    result = await db.execute(select(Season).where(Season.id == season_id))
    season = result.scalar_one_or_none()
    if season is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Season not found")
    return season


@router.get("/{season_id}/standings", response_model=list[SeasonStandingRow])
async def season_standings(season_id: UUID, db: AsyncSession = Depends(get_db)) -> list[SeasonStandingRow]:
    season_result = await db.execute(select(Season).where(Season.id == season_id))
    if season_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Season not found")
    rows = await compute_season_standings(db, season_id)
    return [SeasonStandingRow(**r) for r in rows]
