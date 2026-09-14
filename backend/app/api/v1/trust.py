from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import get_current_user_optional, is_admin
from app.db.session import get_db
from app.models.trust import PlayerTrust
from app.models.user import User
from app.schemas.trust import TrustPublic

router = APIRouter()


@router.get("/{user_id}", response_model=TrustPublic)
async def get_trust(
    user_id: UUID,
    current_user: User | None = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
) -> TrustPublic:
    """Public trust indicator, as rendered on a player profile.

    The endpoint stays reachable without a token — profile.html is a public
    page and shows the trust score to visitors. `disputes_involved` is the one
    field here that is moderation data rather than a reputation signal, and no
    page renders it, so it is returned only to the player themself or to a
    platform admin (the same owner-or-admin rule the analytics endpoint
    already applies to wallet_balance).
    """
    result = await db.execute(select(PlayerTrust).where(PlayerTrust.user_id == user_id))
    trust = result.scalar_one_or_none()
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    privileged = current_user is not None and (
        current_user.id == user_id or await is_admin(db, current_user.id)
    )
    disputes = None
    if trust is not None and privileged:
        disputes = trust.disputes_involved

    return TrustPublic(
        user_id=user.id,
        display_name=user.display_name,
        trust_score=trust.trust_score if trust else 100,
        verified_matches=trust.verified_matches if trust else 0,
        disputes_involved=disputes,
    )
