from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.models.trust import PlayerTrust
from app.models.user import User
from app.schemas.trust import TrustPublic

router = APIRouter()


@router.get("/{user_id}", response_model=TrustPublic)
async def get_trust(user_id: UUID, db: AsyncSession = Depends(get_db)) -> TrustPublic:
    result = await db.execute(
        select(PlayerTrust).options(selectinload(PlayerTrust.__mapper__.class_manager.class_.__table__.columns)) if False else
        select(PlayerTrust).where(PlayerTrust.user_id == user_id)
    )
    trust = result.scalar_one_or_none()
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if trust is None:
        return TrustPublic(
            user_id=user.id,
            display_name=user.display_name,
            trust_score=100,
            verified_matches=0,
            disputes_involved=0,
        )
    return TrustPublic(
        user_id=user.id,
        display_name=user.display_name,
        trust_score=trust.trust_score,
        verified_matches=trust.verified_matches,
        disputes_involved=trust.disputes_involved,
    )
