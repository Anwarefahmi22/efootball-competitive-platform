from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.trust import PlayerTrust, TrustEvent, TrustEventType

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


async def _apply_event(
    db: AsyncSession,
    *,
    user_id: UUID,
    event_type: TrustEventType,
    match_id: UUID,
    delta: int,
    actor_id: UUID | None = None,
    reason: str | None = None,
) -> PlayerTrust | None:
    """Record one trust consequence, or return None if it already happened.

    The audit row is written *first*, inside a SAVEPOINT, and the aggregate
    counters are only touched when that write succeeds. `trust_events` carries
    a unique constraint on (user_id, event_type, match_id), so a repeated or
    concurrent attempt is rejected by the database rather than by an
    application-level check that two requests could both pass. The caller must
    treat a None return as "do nothing at all".
    """
    trust = await get_or_create_trust(db, user_id)
    trust_after = max(0, min(100, trust.trust_score + delta))
    event = TrustEvent(
        id=uuid4(),
        user_id=user_id,
        event_type=event_type,
        match_id=match_id,
        # Store the delta actually applied, after clamping, so the history
        # reconciles with the score it produced.
        delta=trust_after - trust.trust_score,
        trust_after=trust_after,
        actor_id=actor_id,
        reason=reason,
    )
    try:
        async with db.begin_nested():
            db.add(event)
            await db.flush()
    except IntegrityError:
        # uq_trust_event_once_per_match: this event was already applied.
        return None
    trust.trust_score = trust_after
    return trust


async def record_confirmed_match(
    db: AsyncSession, player_a_id: UUID, player_b_id: UUID, match_id: UUID
) -> None:
    for uid in (player_a_id, player_b_id):
        trust = await _apply_event(
            db,
            user_id=uid,
            event_type=TrustEventType.MATCH_CONFIRMED,
            match_id=match_id,
            delta=RECOVERY_PER_VERIFIED_MATCH,
        )
        if trust is not None:
            trust.verified_matches += 1


async def record_dispute_filed(
    db: AsyncSession, disputer_id: UUID, submitter_id: UUID, match_id: UUID
) -> None:
    # Filing a dispute is a signal for review, not an offence: it moves no
    # trust score. Only the resolution carries a consequence.
    for uid in (disputer_id, submitter_id):
        trust = await _apply_event(
            db,
            user_id=uid,
            event_type=TrustEventType.DISPUTE_FILED,
            match_id=match_id,
            delta=0,
        )
        if trust is not None:
            trust.disputes_involved += 1


async def record_dispute_resolved(
    db: AsyncSession,
    submitter_id: UUID,
    disputer_id: UUID,
    submitter_was_correct: bool,
    match_id: UUID,
    admin_id: UUID | None = None,
) -> None:
    """Apply the single trust consequence of an administrative decision.

    `admin_id` is recorded on the event so the decision is attributable; the
    match itself has no resolved_by column and never has had one.
    """
    if submitter_was_correct:
        trust = await _apply_event(
            db,
            user_id=disputer_id,
            event_type=TrustEventType.DISPUTE_RESOLVED,
            match_id=match_id,
            delta=-DISPUTE_PENALTY,
            actor_id=admin_id,
            reason="submitter_correct",
        )
        if trust is not None:
            trust.unjustified_disputes += 1
    else:
        trust = await _apply_event(
            db,
            user_id=submitter_id,
            event_type=TrustEventType.DISPUTE_RESOLVED,
            match_id=match_id,
            delta=-FALSE_REPORT_PENALTY,
            actor_id=admin_id,
            reason="false_report",
        )
        if trust is not None:
            trust.false_reports += 1
