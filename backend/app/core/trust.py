from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.trust import PlayerTrust

DISPUTE_PENALTY = 10
FALSE_REPORT_PENALTY = 15
RECOVERY_PER_VERIFIED_MATCH = 1


async def get_or_create_trust(db: AsyncSession, user_id: UUID) -> PlayerTrust:
    result = await db.execute(select(PlayerTrust).where(PlayerTrust.user_id == user_id))
    trust = result.scalar_one_or_none()
    if trust is None:
        trust = PlayerTrust(user_id=user_id, trust_score=100)
        db.add(trust)
        await db.flush()
    return trust


async def record_confirmed_match(db: AsyncSession, player_a_id: UUID, player_b_id: UUID) -> None:
    for uid in (player_a_id, player_b_id):
        trust = await get_or_create_trust(db, uid)
        trust.verified_matches += 1
        trust.trust_score = min(100, trust.trust_score + RECOVERY_PER_VERIFIED_MATCH)


async def record_dispute_filed(db: AsyncSession, disputer_id: UUID, submitter_id: UUID) -> None:
    for uid in (disputer_id, submitter_id):
        trust = await get_or_create_trust(db, uid)
        trust.disputes_involved += 1


async def record_dispute_resolved(
    db: AsyncSession, submitter_id: UUID, disputer_id: UUID, submitter_was_correct: bool
) -> None:
    if submitter_was_correct:
        disputer_trust = await get_or_create_trust(db, disputer_id)
        disputer_trust.unjustified_disputes += 1
        disputer_trust.trust_score = max(0, disputer_trust.trust_score - DISPUTE_PENALTY)
    else:
        submitter_trust = await get_or_create_trust(db, submitter_id)
        submitter_trust.false_reports += 1
        submitter_trust.trust_score = max(0, submitter_trust.trust_score - FALSE_REPORT_PENALTY)
