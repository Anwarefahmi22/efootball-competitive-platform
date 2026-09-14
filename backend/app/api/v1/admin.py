"""Administrative surface: the dispute queue, dispute review and trust history.

Every route here is gated by `get_current_admin`, so authorization is enforced
by a FastAPI dependency rather than by the caller remembering to check. These
endpoints are read-only: the authoritative decision is still made through
POST /matches/{id}/resolve-dispute, which keeps its Phase 3 compare-and-swap
protection. This module deliberately adds no second path to the same effect.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import get_current_admin
from app.db.session import get_db
from app.models.evidence import MatchEvidence
from app.models.match import Match, MatchStatus
from app.models.tournament import Tournament
from app.models.trust import PlayerTrust, TrustEvent
from app.models.user import User
from app.schemas.trust import (
    DisputeDetail,
    DisputeEvidenceRead,
    DisputeQueueItem,
    TrustEventRead,
)

router = APIRouter()

# `matches` has no disputed_at column. updated_at is written by the same
# transaction that flips the row to DISPUTED and nothing else touches a
# disputed match, so it is the dispute timestamp in practice.
DEFAULT_TRUST = 100


async def _names(db: AsyncSession, user_ids: set[UUID]) -> dict[UUID, str]:
    if not user_ids:
        return {}
    rows = await db.execute(select(User.id, User.display_name).where(User.id.in_(user_ids)))
    return {row.id: row.display_name for row in rows.all()}


async def _trust_scores(db: AsyncSession, user_ids: set[UUID]) -> dict[UUID, int]:
    if not user_ids:
        return {}
    rows = await db.execute(
        select(PlayerTrust.user_id, PlayerTrust.trust_score).where(PlayerTrust.user_id.in_(user_ids))
    )
    return {row.user_id: row.trust_score for row in rows.all()}


async def _dispute_matches(
    db: AsyncSession, state: str, limit: int, offset: int
) -> list[Match]:
    stmt = select(Match).where(Match.disputed_by.isnot(None))
    if state == "disputed":
        stmt = stmt.where(Match.status == MatchStatus.DISPUTED)
    elif state == "resolved":
        stmt = stmt.where(Match.status.in_([MatchStatus.COMPLETED, MatchStatus.CANCELLED]))
    elif state != "all":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown dispute state")
    # `Match.id` is the tiebreaker, not decoration: this endpoint paginates,
    # and ORDER BY on a non-unique column lets LIMIT/OFFSET return the same row
    # twice or skip one between pages. Two matches disputed in the same instant
    # are otherwise unordered.
    stmt = stmt.order_by(Match.updated_at.desc(), Match.id.desc()).limit(limit).offset(offset)
    return list((await db.execute(stmt)).scalars().all())


@router.get("/disputes", response_model=list[DisputeQueueItem])
async def dispute_queue(
    state: str = Query(default="disputed", alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> list[DisputeQueueItem]:
    """Matches a moderator has to look at, newest first."""
    matches = await _dispute_matches(db, state, limit, offset)
    if not matches:
        return []

    match_ids = [m.id for m in matches]
    tour_rows = await db.execute(
        select(Tournament.id, Tournament.name, Tournament.format).where(
            Tournament.id.in_({m.tournament_id for m in matches})
        )
    )
    tournaments = {row.id: row for row in tour_rows.all()}

    ev_rows = await db.execute(
        select(
            MatchEvidence.match_id,
            func.count().label("n"),
        )
        .where(MatchEvidence.match_id.in_(match_ids))
        .group_by(MatchEvidence.match_id)
    )
    counts = {row.match_id: row.n for row in ev_rows.all()}

    # The claim under review is the newest evidence row, matching what
    # /confirm and /resolve-dispute act on.
    latest_rows = await db.execute(
        select(MatchEvidence)
        .where(MatchEvidence.match_id.in_(match_ids))
        .order_by(MatchEvidence.created_at.desc())
    )
    latest: dict[UUID, MatchEvidence] = {}
    for ev in latest_rows.scalars().all():
        latest.setdefault(ev.match_id, ev)

    people = {m.player_a_id for m in matches} | {m.player_b_id for m in matches}
    people |= {m.disputed_by for m in matches if m.disputed_by}
    people |= {ev.submitted_by for ev in latest.values()}
    names = await _names(db, {p for p in people if p})
    trust = await _trust_scores(db, {m.player_a_id for m in matches} | {m.player_b_id for m in matches})

    out = []
    for m in matches:
        ev = latest.get(m.id)
        if ev is None:
            # A disputed match with no evidence cannot be reviewed; skip it
            # rather than inventing a claim.
            continue
        tour = tournaments.get(m.tournament_id)
        out.append(
            DisputeQueueItem(
                match_id=m.id,
                status=m.status.value if hasattr(m.status, "value") else str(m.status),
                tournament_id=m.tournament_id,
                tournament_name=tour.name if tour else "",
                tournament_format=tour.format if tour else "",
                round_number=m.round_number,
                player_a_id=m.player_a_id,
                player_a_name=names.get(m.player_a_id, ""),
                player_a_trust=trust.get(m.player_a_id, DEFAULT_TRUST),
                player_b_id=m.player_b_id,
                player_b_name=names.get(m.player_b_id, ""),
                player_b_trust=trust.get(m.player_b_id, DEFAULT_TRUST),
                submitted_by=ev.submitted_by,
                submitted_by_name=names.get(ev.submitted_by, ""),
                claimed_score_a=ev.claimed_score_a,
                claimed_score_b=ev.claimed_score_b,
                disputed_by=m.disputed_by,
                disputed_by_name=names.get(m.disputed_by, "") if m.disputed_by else None,
                evidence_count=counts.get(m.id, 0),
                has_evidence=counts.get(m.id, 0) > 0,
                disputed_at=m.updated_at,
            )
        )
    return out


@router.get("/disputes/{match_id}", response_model=DisputeDetail)
async def dispute_detail(
    match_id: UUID,
    _admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> DisputeDetail:
    result = await db.execute(select(Match).where(Match.id == match_id))
    match = result.scalar_one_or_none()
    if match is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found")
    if match.disputed_by is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="This match has no dispute")

    tour = (
        await db.execute(
            select(Tournament).where(Tournament.id == match.tournament_id)
        )
    ).scalar_one_or_none()

    ev_rows = await db.execute(
        select(MatchEvidence)
        .where(MatchEvidence.match_id == match_id)
        .order_by(MatchEvidence.created_at.desc())
    )
    evidence = list(ev_rows.scalars().all())
    if not evidence:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="This dispute has no evidence on file"
        )
    latest_ev = evidence[0]

    people = {match.player_a_id, match.player_b_id, latest_ev.submitted_by}
    if match.disputed_by:
        people.add(match.disputed_by)
    names = await _names(db, {p for p in people if p})
    trust = await _trust_scores(db, {match.player_a_id, match.player_b_id})

    # A fraud *signal*, presented as a count and nothing more. It is not a
    # finding and it changes no state.
    together = (
        await db.execute(
            select(func.count())
            .select_from(Match)
            .where(
                Match.status == MatchStatus.COMPLETED,
                (
                    (Match.player_a_id == match.player_a_id)
                    & (Match.player_b_id == match.player_b_id)
                )
                | (
                    (Match.player_a_id == match.player_b_id)
                    & (Match.player_b_id == match.player_a_id)
                ),
            )
        )
    ).scalar_one()

    return DisputeDetail(
        match_id=match.id,
        status=match.status.value if hasattr(match.status, "value") else str(match.status),
        tournament_id=match.tournament_id,
        tournament_name=tour.name if tour else "",
        tournament_format=tour.format if tour else "",
        round_number=match.round_number,
        player_a_id=match.player_a_id,
        player_a_name=names.get(match.player_a_id, ""),
        player_a_trust=trust.get(match.player_a_id, DEFAULT_TRUST),
        player_b_id=match.player_b_id,
        player_b_name=names.get(match.player_b_id, ""),
        player_b_trust=trust.get(match.player_b_id, DEFAULT_TRUST),
        submitted_by=latest_ev.submitted_by,
        submitted_by_name=names.get(latest_ev.submitted_by, ""),
        claimed_score_a=latest_ev.claimed_score_a,
        claimed_score_b=latest_ev.claimed_score_b,
        disputed_by=match.disputed_by,
        disputed_by_name=names.get(match.disputed_by, "") if match.disputed_by else None,
        evidence_count=len(evidence),
        has_evidence=True,
        disputed_at=match.updated_at,
        evidence=[
            DisputeEvidenceRead(
                id=e.id,
                submitted_by=e.submitted_by,
                claimed_score_a=e.claimed_score_a,
                claimed_score_b=e.claimed_score_b,
                has_image=e.image_data is not None,
                created_at=e.created_at,
            )
            for e in evidence
        ],
        collusion_matches_together=together,
    )


@router.get("/trust/{user_id}/events", response_model=list[TrustEventRead])
async def trust_history(
    user_id: UUID,
    limit: int = Query(default=100, ge=1, le=500),
    _admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> list[TrustEventRead]:
    """Why a player's trust is what it is. Admin-only: this is moderation
    history, not the public trust indicator shown on a profile."""
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    rows = await db.execute(
        select(TrustEvent)
        .where(TrustEvent.user_id == user_id)
        # Trailing id keeps the history totally ordered for the same reason.
        .order_by(TrustEvent.created_at.desc(), TrustEvent.id.desc())
        .limit(limit)
    )
    return [
        TrustEventRead(
            id=e.id,
            event_type=e.event_type.value if hasattr(e.event_type, "value") else str(e.event_type),
            delta=e.delta,
            trust_after=e.trust_after,
            match_id=e.match_id,
            actor_id=e.actor_id,
            reason=e.reason,
            created_at=e.created_at,
        )
        for e in rows.scalars().all()
    ]
