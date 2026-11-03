"""Phase 2: in-app invites + ELO challenge matches.

Match invites and tournament invites share one inbox and one bell count.
Accepting a match invite creates a ChallengeMatch; its result flow mirrors
tournament matches (submit with evidence screenshot -> opponent confirms or
disputes -> admin resolves disputes) and confirmed results move ELO through
the very same helpers tournament matches use, so a challenge win is worth
exactly what a tournament win is worth. Anti-farming guards (approved with
the phase): one open challenge per pair, a 24h pair cooldown after a
completed challenge, and at most 5 completed challenges per player per 24h.
"""
import uuid as uuid_module
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import Response
from sqlalchemy import func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_user
from app.api.v1.matches import _apply_elo_draw, _apply_elo_win
from app.core.competition import MAX_SCORE
from app.core.media import evidence_media_type, normalize_image, read_upload_limited
from app.core.permissions import get_current_admin
from app.core.storage import MAX_UPLOAD_BYTES
from app.core.trust import record_confirmed_match, record_dispute_filed, record_dispute_resolved
from app.db.session import get_db
from app.models.invite import (
    ChallengeEvidence,
    ChallengeMatch,
    ChallengeStatus,
    InviteStatus,
    MatchInvite,
    TournamentInvite,
)
from app.models.tournament import Tournament, TournamentParticipant, TournamentStatus
from app.models.user import Profile, User
from app.schemas.evidence import DisputeCreate, ResolveDispute
from app.schemas.invite import (
    ChallengeEvidenceRead,
    ChallengeRead,
    InviteCountRead,
    InviteInboxRead,
    MatchInviteCreate,
    MatchInviteRead,
    PlayerBrief,
    TournamentInviteCreate,
    TournamentInviteRead,
)

invites_router = APIRouter()
challenges_router = APIRouter()

MATCH_INVITE_TTL = timedelta(hours=72)
TOURNAMENT_INVITE_TTL = timedelta(days=7)
PAIR_COOLDOWN = timedelta(hours=24)
DAILY_CHALLENGE_CAP = 5
OPEN_CHALLENGE_STATUSES = {
    ChallengeStatus.READY,
    ChallengeStatus.RESULT_SUBMITTED,
    ChallengeStatus.DISPUTED,
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def _briefs(db: AsyncSession, user_ids: set[UUID]) -> dict[UUID, PlayerBrief]:
    """Batch-load player briefs in two queries total (AUD-05).

    The per-invite loader this replaces ran two queries PER brief, so
    an inbox of N invites cost ~4N+ queries. Profile has its own PK;
    user_id is a unique FK — profiles must be selected by user_id, not
    fetched with db.get(Profile, ...) (which silently missed every
    profile and lost the avatars).
    """
    if not user_ids:
        return {}
    users = {
        u.id: u
        for u in (await db.execute(select(User).where(User.id.in_(user_ids)))).scalars()
    }
    profiles = {
        p.user_id: p
        for p in (
            await db.execute(select(Profile).where(Profile.user_id.in_(user_ids)))
        ).scalars()
    }
    out: dict[UUID, PlayerBrief] = {}
    for user_id in user_ids:
        user = users.get(user_id)
        profile = profiles.get(user_id)
        out[user_id] = PlayerBrief(
            user_id=user_id,
            display_name=user.display_name if user else "لاعب",
            avatar_url=profile.avatar_url if profile else None,
            arena_no=user.arena_no if user else None,
        )
    return out


async def _brief(db: AsyncSession, user_id: UUID) -> PlayerBrief:
    return (await _briefs(db, {user_id}))[user_id]


def _effective_status(invite, ttl: timedelta) -> str:
    if invite.status == InviteStatus.PENDING and invite.created_at < _now() - ttl:
        return "expired"
    return str(invite.status)


def _match_invite_read_from(briefs: dict[UUID, PlayerBrief], invite: MatchInvite) -> MatchInviteRead:
    return MatchInviteRead(
        id=invite.id,
        challenger=briefs[invite.challenger_id],
        opponent=briefs[invite.opponent_id],
        status=_effective_status(invite, MATCH_INVITE_TTL),
        challenge_id=invite.challenge_id,
        created_at=invite.created_at,
        responded_at=invite.responded_at,
    )


async def _match_invite_read(db: AsyncSession, invite: MatchInvite) -> MatchInviteRead:
    briefs = await _briefs(db, {invite.challenger_id, invite.opponent_id})
    return _match_invite_read_from(briefs, invite)


async def _match_invite_reads(db: AsyncSession, invites: list[MatchInvite]) -> list[MatchInviteRead]:
    briefs = await _briefs(
        db, {i.challenger_id for i in invites} | {i.opponent_id for i in invites}
    )
    return [_match_invite_read_from(briefs, i) for i in invites]


def _tournament_invite_read_from(
    briefs: dict[UUID, PlayerBrief],
    tournaments: dict[UUID, Tournament],
    invite: TournamentInvite,
) -> TournamentInviteRead:
    tournament = tournaments.get(invite.tournament_id)
    return TournamentInviteRead(
        id=invite.id,
        tournament_id=invite.tournament_id,
        tournament_name=tournament.name if tournament else "بطولة",
        inviter=briefs[invite.inviter_id],
        invitee=briefs[invite.invitee_id],
        status=_effective_status(invite, TOURNAMENT_INVITE_TTL),
        created_at=invite.created_at,
        responded_at=invite.responded_at,
    )


async def _tournament_invite_read(db: AsyncSession, invite: TournamentInvite) -> TournamentInviteRead:
    briefs = await _briefs(db, {invite.inviter_id, invite.invitee_id})
    tournament = await db.get(Tournament, invite.tournament_id)
    tournaments = {tournament.id: tournament} if tournament else {}
    return _tournament_invite_read_from(briefs, tournaments, invite)


async def _tournament_invite_reads(
    db: AsyncSession, invites: list[TournamentInvite]
) -> list[TournamentInviteRead]:
    briefs = await _briefs(
        db, {i.inviter_id for i in invites} | {i.invitee_id for i in invites}
    )
    tournaments = {}
    if invites:
        tournaments = {
            t.id: t
            for t in (
                await db.execute(
                    select(Tournament).where(
                        Tournament.id.in_({i.tournament_id for i in invites})
                    )
                )
            ).scalars()
        }
    return [_tournament_invite_read_from(briefs, tournaments, i) for i in invites]


def _pair_filter(a: UUID, b: UUID):
    return or_(
        (ChallengeMatch.player_a_id == a) & (ChallengeMatch.player_b_id == b),
        (ChallengeMatch.player_a_id == b) & (ChallengeMatch.player_b_id == a),
    )


async def _open_challenge_between(db: AsyncSession, a: UUID, b: UUID) -> ChallengeMatch | None:
    result = await db.execute(
        select(ChallengeMatch).where(
            _pair_filter(a, b), ChallengeMatch.status.in_(OPEN_CHALLENGE_STATUSES)
        )
    )
    return result.scalars().first()


async def _pair_on_cooldown(db: AsyncSession, a: UUID, b: UUID) -> bool:
    result = await db.execute(
        select(func.count(ChallengeMatch.id)).where(
            _pair_filter(a, b),
            ChallengeMatch.status == ChallengeStatus.COMPLETED,
            ChallengeMatch.completed_at >= _now() - PAIR_COOLDOWN,
        )
    )
    return (result.scalar() or 0) > 0


async def _player_at_daily_cap(db: AsyncSession, user_id: UUID) -> bool:
    result = await db.execute(
        select(func.count(ChallengeMatch.id)).where(
            or_(ChallengeMatch.player_a_id == user_id, ChallengeMatch.player_b_id == user_id),
            ChallengeMatch.status == ChallengeStatus.COMPLETED,
            ChallengeMatch.completed_at >= _now() - PAIR_COOLDOWN,
        )
    )
    return (result.scalar() or 0) >= DAILY_CHALLENGE_CAP


async def _check_pair_can_play(db: AsyncSession, a: UUID, b: UUID) -> None:
    """The anti-farming gate, applied identically at invite-send and accept."""
    if await _open_challenge_between(db, a, b) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="يوجد تحدٍّ مفتوح بينكما بالفعل — أكملاه أولًا",
        )
    if await _pair_on_cooldown(db, a, b):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="لا يمكنكما لعب تحدٍّ محسوب جديد قبل مرور 24 ساعة على التحدي السابق بينكما",
        )
    for uid in (a, b):
        if await _player_at_daily_cap(db, uid):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="تم بلوغ الحد اليومي للتحديات المحسوبة (5 خلال 24 ساعة)",
            )


async def _claim_challenge_state(
    db: AsyncSession, challenge_id: UUID, expected: set, target: str
) -> bool:
    """Same compare-and-swap discipline as tournament matches: exactly one
    request may move a challenge out of `expected`, so ELO can never be
    applied twice for one result."""
    result = await db.execute(
        update(ChallengeMatch)
        .where(ChallengeMatch.id == challenge_id, ChallengeMatch.status.in_(expected))
        .values(status=target)
        .execution_options(synchronize_session=False)
    )
    return result.rowcount == 1


async def _finalize_challenge(
    db: AsyncSession, challenge: ChallengeMatch, score_a: int, score_b: int
) -> None:
    challenge.score_a = score_a
    challenge.score_b = score_b
    challenge.status = ChallengeStatus.COMPLETED
    challenge.completed_at = _now()
    if score_a == score_b:
        challenge.winner_id = None
        await _apply_elo_draw(db, challenge.player_a_id, challenge.player_b_id, score_a, score_b)
    else:
        winner_id = challenge.player_a_id if score_a > score_b else challenge.player_b_id
        loser_id = challenge.player_b_id if winner_id == challenge.player_a_id else challenge.player_a_id
        challenge.winner_id = winner_id
        winner_goals, loser_goals = (
            (score_a, score_b) if winner_id == challenge.player_a_id else (score_b, score_a)
        )
        await _apply_elo_win(db, winner_id, loser_id, winner_goals, loser_goals)


async def _latest_evidence(db: AsyncSession, challenge_id: UUID) -> ChallengeEvidence | None:
    result = await db.execute(
        select(ChallengeEvidence)
        .where(ChallengeEvidence.challenge_id == challenge_id)
        .order_by(ChallengeEvidence.created_at.desc())
    )
    return result.scalars().first()


def _challenge_read_from(
    briefs: dict[UUID, PlayerBrief],
    challenge: ChallengeMatch,
    evidence: ChallengeEvidence | None,
) -> ChallengeRead:
    read = ChallengeRead(
        id=challenge.id,
        invite_id=challenge.invite_id,
        player_a=briefs[challenge.player_a_id],
        player_b=briefs[challenge.player_b_id],
        status=str(challenge.status),
        score_a=challenge.score_a,
        score_b=challenge.score_b,
        winner_id=challenge.winner_id,
        disputed_by=challenge.disputed_by,
        completed_at=challenge.completed_at,
        created_at=challenge.created_at,
    )
    if (
        challenge.status in {ChallengeStatus.RESULT_SUBMITTED, ChallengeStatus.DISPUTED}
        and evidence is not None
    ):
        read.pending_submitted_by = evidence.submitted_by
        read.pending_score_a = evidence.claimed_score_a
        read.pending_score_b = evidence.claimed_score_b
        read.pending_evidence_id = evidence.id
    return read


async def _challenge_read(db: AsyncSession, challenge: ChallengeMatch) -> ChallengeRead:
    briefs = await _briefs(db, {challenge.player_a_id, challenge.player_b_id})
    evidence = None
    if challenge.status in {ChallengeStatus.RESULT_SUBMITTED, ChallengeStatus.DISPUTED}:
        evidence = await _latest_evidence(db, challenge.id)
    return _challenge_read_from(briefs, challenge, evidence)


async def _challenge_reads(
    db: AsyncSession, challenges: list[ChallengeMatch]
) -> list[ChallengeRead]:
    """Batch variant (AUD-05): briefs in 2 queries, latest evidence for
    every pending challenge in 1 query — constant in the list size."""
    briefs = await _briefs(
        db, {c.player_a_id for c in challenges} | {c.player_b_id for c in challenges}
    )
    pending_ids = [
        c.id
        for c in challenges
        if c.status in {ChallengeStatus.RESULT_SUBMITTED, ChallengeStatus.DISPUTED}
    ]
    latest: dict[UUID, ChallengeEvidence] = {}
    if pending_ids:
        rows = (
            await db.execute(
                select(ChallengeEvidence)
                .where(ChallengeEvidence.challenge_id.in_(pending_ids))
                .order_by(ChallengeEvidence.created_at.desc())
            )
        ).scalars()
        for ev in rows:
            latest.setdefault(ev.challenge_id, ev)
    return [_challenge_read_from(briefs, c, latest.get(c.id)) for c in challenges]


# ---------------------------------------------------------------- invites

@invites_router.post("/match", response_model=MatchInviteRead, status_code=status.HTTP_201_CREATED)
async def send_match_invite(
    payload: MatchInviteCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MatchInviteRead:
    if payload.opponent_id == current_user.id:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="لا يمكنك دعوة نفسك")
    opponent = await db.get(User, payload.opponent_id)
    if opponent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="اللاعب غير موجود")
    pending = await db.execute(
        select(MatchInvite).where(
            MatchInvite.status == InviteStatus.PENDING,
            MatchInvite.created_at >= _now() - MATCH_INVITE_TTL,
            or_(
                (MatchInvite.challenger_id == current_user.id) & (MatchInvite.opponent_id == payload.opponent_id),
                (MatchInvite.challenger_id == payload.opponent_id) & (MatchInvite.opponent_id == current_user.id),
            ),
        )
    )
    if pending.scalars().first() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="توجد دعوة معلّقة بينكما بالفعل")
    await _check_pair_can_play(db, current_user.id, payload.opponent_id)
    invite = MatchInvite(challenger_id=current_user.id, opponent_id=payload.opponent_id)
    db.add(invite)
    try:
        await db.commit()
    except IntegrityError:
        # AUD-13: the canonical pair index (migration 020) fired — a
        # simultaneous invite in the opposite direction won the race.
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="توجد دعوة معلّقة بينكما بالفعل")
    await db.refresh(invite)
    return await _match_invite_read(db, invite)


@invites_router.post("/match/{invite_id}/accept", response_model=ChallengeRead, status_code=status.HTTP_201_CREATED)
async def accept_match_invite(
    invite_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ChallengeRead:
    invite = await _load_actionable_invite(db, MatchInvite, invite_id, actor_id=current_user.id, actor_field="opponent_id", actor_error="هذه الدعوة ليست موجّهة إليك", ttl=MATCH_INVITE_TTL)
    await _check_pair_can_play(db, invite.challenger_id, invite.opponent_id)
    challenge = ChallengeMatch(
        invite_id=invite.id, player_a_id=invite.challenger_id, player_b_id=invite.opponent_id
    )
    db.add(challenge)
    try:
        await db.flush()
        invite.status = InviteStatus.ACCEPTED
        invite.challenge_id = challenge.id
        invite.responded_at = _now()
        await db.commit()
    except IntegrityError:
        # AUD-15: a concurrent accept of the same invite won the race —
        # challenge_matches.invite_id is unique, so translate the database
        # conflict into the controlled response instead of a 500.
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="تم إنشاء تحدٍّ لهذه الدعوة من قبل",
        )
    await db.refresh(challenge)
    return await _challenge_read(db, challenge)


async def _load_actionable_invite(
    db: AsyncSession,
    model,
    invite_id: UUID,
    *,
    actor_id: UUID,
    actor_field: str,
    actor_error: str,
    ttl: timedelta | None = None,
):
    """AUD-31: the guard sequence every invite response shares —
    exists (404) -> addressed to the caller (403) -> still pending
    (400) -> not expired (410, accepts only). Six handlers used to
    repeat it verbatim; the messages are part of the API contract and
    are preserved exactly.
    """
    invite = await db.get(model, invite_id)
    if invite is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الدعوة غير موجودة")
    if getattr(invite, actor_field) != actor_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=actor_error)
    if invite.status != InviteStatus.PENDING:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="تم الرد على هذه الدعوة من قبل")
    if ttl is not None and invite.created_at < _now() - ttl:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="انتهت صلاحية هذه الدعوة")
    return invite


async def _respond_match_invite(db: AsyncSession, invite: MatchInvite, new_status: str) -> None:
    invite.status = new_status
    invite.responded_at = _now()
    await db.commit()
    await db.refresh(invite)


@invites_router.post("/match/{invite_id}/decline", response_model=MatchInviteRead)
async def decline_match_invite(
    invite_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MatchInviteRead:
    invite = await _load_actionable_invite(db, MatchInvite, invite_id, actor_id=current_user.id, actor_field="opponent_id", actor_error="هذه الدعوة ليست موجّهة إليك")
    await _respond_match_invite(db, invite, InviteStatus.DECLINED)
    return await _match_invite_read(db, invite)


@invites_router.delete("/match/{invite_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_match_invite(
    invite_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    invite = await _load_actionable_invite(db, MatchInvite, invite_id, actor_id=current_user.id, actor_field="challenger_id", actor_error="يمكنك إلغاء دعواتك فقط")
    await _respond_match_invite(db, invite, InviteStatus.CANCELLED)


@invites_router.post("/tournament", response_model=TournamentInviteRead, status_code=status.HTTP_201_CREATED)
async def send_tournament_invite(
    payload: TournamentInviteCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TournamentInviteRead:
    tournament = await db.get(Tournament, payload.tournament_id)
    if tournament is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="البطولة غير موجودة")
    if tournament.created_by != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="يمكن لمنظّم البطولة فقط إرسال دعوات إليها")
    if tournament.status != TournamentStatus.REGISTRATION_OPEN:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="التسجيل في هذه البطولة غير مفتوح")
    if payload.invitee_id == current_user.id:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="لا يمكنك دعوة نفسك")
    invitee = await db.get(User, payload.invitee_id)
    if invitee is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="اللاعب غير موجود")
    joined = await db.execute(
        select(TournamentParticipant).where(
            TournamentParticipant.tournament_id == tournament.id,
            TournamentParticipant.user_id == payload.invitee_id,
        )
    )
    if joined.scalars().first() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="هذا اللاعب مسجّل في البطولة بالفعل")
    pending = await db.execute(
        select(TournamentInvite).where(
            TournamentInvite.tournament_id == tournament.id,
            TournamentInvite.invitee_id == payload.invitee_id,
            TournamentInvite.status == InviteStatus.PENDING,
            TournamentInvite.created_at >= _now() - TOURNAMENT_INVITE_TTL,
        )
    )
    if pending.scalars().first() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="توجد دعوة معلّقة لهذا اللاعب إلى هذه البطولة")
    invite = TournamentInvite(
        tournament_id=tournament.id, inviter_id=current_user.id, invitee_id=payload.invitee_id
    )
    db.add(invite)
    await db.commit()
    await db.refresh(invite)
    return await _tournament_invite_read(db, invite)


@invites_router.post("/tournament/{invite_id}/accept", response_model=TournamentInviteRead)
async def accept_tournament_invite(
    invite_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TournamentInviteRead:
    invite = await _load_actionable_invite(db, TournamentInvite, invite_id, actor_id=current_user.id, actor_field="invitee_id", actor_error="هذه الدعوة ليست موجّهة إليك", ttl=TOURNAMENT_INVITE_TTL)
    # AUD-06: lock the tournament row (same lock join_tournament takes)
    # so the capacity re-check below and the participant insert are
    # atomic against concurrent joins and accepts.
    locked = await db.execute(
        select(Tournament).where(Tournament.id == invite.tournament_id).with_for_update()
    )
    tournament = locked.scalar_one_or_none()
    if tournament is None or tournament.status != TournamentStatus.REGISTRATION_OPEN:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="التسجيل في هذه البطولة لم يعد مفتوحًا")
    participants = await db.execute(
        select(TournamentParticipant).where(TournamentParticipant.tournament_id == tournament.id)
    )
    rows = list(participants.scalars().all())
    if any(p.user_id == current_user.id for p in rows):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="أنت مسجّل في هذه البطولة بالفعل")
    if len(rows) >= tournament.max_participants:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="امتلأت البطولة")
    # The inviter is the organizer, so their invitation is itself the
    # approval: the participant enters as approved even when the tournament
    # otherwise requires manual approval.
    db.add(TournamentParticipant(tournament_id=tournament.id, user_id=current_user.id, status="approved"))
    invite.status = InviteStatus.ACCEPTED
    invite.responded_at = _now()
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="أنت مسجّل في هذه البطولة بالفعل")
    await db.refresh(invite)
    return await _tournament_invite_read(db, invite)


@invites_router.post("/tournament/{invite_id}/decline", response_model=TournamentInviteRead)
async def decline_tournament_invite(
    invite_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TournamentInviteRead:
    invite = await _load_actionable_invite(db, TournamentInvite, invite_id, actor_id=current_user.id, actor_field="invitee_id", actor_error="هذه الدعوة ليست موجّهة إليك")
    invite.status = InviteStatus.DECLINED
    invite.responded_at = _now()
    await db.commit()
    await db.refresh(invite)
    return await _tournament_invite_read(db, invite)


@invites_router.delete("/tournament/{invite_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_tournament_invite(
    invite_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    invite = await _load_actionable_invite(db, TournamentInvite, invite_id, actor_id=current_user.id, actor_field="inviter_id", actor_error="يمكنك إلغاء دعواتك فقط")
    invite.status = InviteStatus.CANCELLED
    invite.responded_at = _now()
    await db.commit()


@invites_router.get("", response_model=InviteInboxRead)
async def get_inbox(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InviteInboxRead:
    async def _list(model, column, uid):
        result = await db.execute(
            select(model).where(column == uid).order_by(model.created_at.desc()).limit(50)
        )
        return list(result.scalars().all())

    match_received = await _list(MatchInvite, MatchInvite.opponent_id, current_user.id)
    match_sent = await _list(MatchInvite, MatchInvite.challenger_id, current_user.id)
    tour_received = await _list(TournamentInvite, TournamentInvite.invitee_id, current_user.id)
    tour_sent = await _list(TournamentInvite, TournamentInvite.inviter_id, current_user.id)
    return InviteInboxRead(
        match_received=await _match_invite_reads(db, match_received),
        match_sent=await _match_invite_reads(db, match_sent),
        tournament_received=await _tournament_invite_reads(db, tour_received),
        tournament_sent=await _tournament_invite_reads(db, tour_sent),
    )


@invites_router.get("/count", response_model=InviteCountRead)
async def get_invite_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InviteCountRead:
    match_count = await db.execute(
        select(func.count(MatchInvite.id)).where(
            MatchInvite.opponent_id == current_user.id,
            MatchInvite.status == InviteStatus.PENDING,
            MatchInvite.created_at >= _now() - MATCH_INVITE_TTL,
        )
    )
    tour_count = await db.execute(
        select(func.count(TournamentInvite.id)).where(
            TournamentInvite.invitee_id == current_user.id,
            TournamentInvite.status == InviteStatus.PENDING,
            TournamentInvite.created_at >= _now() - TOURNAMENT_INVITE_TTL,
        )
    )
    return InviteCountRead(pending_received=(match_count.scalar() or 0) + (tour_count.scalar() or 0))


# ------------------------------------------------------------- challenges

@challenges_router.get("", response_model=list[ChallengeRead])
async def list_challenges(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ChallengeRead]:
    result = await db.execute(
        select(ChallengeMatch)
        .where(or_(ChallengeMatch.player_a_id == current_user.id, ChallengeMatch.player_b_id == current_user.id))
        .order_by(ChallengeMatch.created_at.desc())
        .limit(50)
    )
    return await _challenge_reads(db, list(result.scalars().all()))


async def _get_challenge_or_404(db: AsyncSession, challenge_id: UUID) -> ChallengeMatch:
    challenge = await db.get(ChallengeMatch, challenge_id)
    if challenge is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="التحدي غير موجود")
    return challenge


def _require_participant(challenge: ChallengeMatch, user: User) -> None:
    if user.id not in {challenge.player_a_id, challenge.player_b_id}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="لست طرفًا في هذا التحدي")


@challenges_router.post("/{challenge_id}/submit-result", response_model=ChallengeEvidenceRead, status_code=status.HTTP_201_CREATED)
async def submit_challenge_result(
    challenge_id: UUID,
    score_a: int = Form(...),
    score_b: int = Form(...),
    image: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ChallengeEvidence:
    challenge = await _get_challenge_or_404(db, challenge_id)
    _require_participant(challenge, current_user)
    if score_a < 0 or score_b < 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="لا يمكن أن تكون النتيجة سالبة")
    if score_a > MAX_SCORE or score_b > MAX_SCORE:
        # AUD-25: same plausibility cap as tournament matches.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"لا يمكن أن تتجاوز النتيجة {MAX_SCORE}",
        )
    if challenge.status != ChallengeStatus.READY:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="هذا التحدي لا يقبل إرسال نتيجة الآن")
    # AUD-12/AUD-16: streamed size cap, then Pillow decode + WebP
    # re-encode — identical image policy to tournament evidence.
    raw_bytes = await read_upload_limited(image, MAX_UPLOAD_BYTES)
    try:
        file_bytes = normalize_image(raw_bytes, max_width=2048, quality=88)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="الملف المرفوع ليس صورة صالحة",
        )
    if not await _claim_challenge_state(db, challenge.id, {ChallengeStatus.READY}, ChallengeStatus.RESULT_SUBMITTED):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="تم إرسال نتيجة لهذا التحدي بالفعل")
    extension = ".webp"
    evidence = ChallengeEvidence(
        challenge_id=challenge.id,
        submitted_by=current_user.id,
        claimed_score_a=score_a,
        claimed_score_b=score_b,
        image_path=f"{challenge_id}_{uuid_module.uuid4().hex}{extension}",
        image_data=file_bytes,
    )
    db.add(evidence)
    await db.commit()
    await db.refresh(evidence)
    return evidence


@challenges_router.get("/{challenge_id}/evidence", response_model=list[ChallengeEvidenceRead])
async def list_challenge_evidence(
    challenge_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ChallengeEvidence]:
    challenge = await _get_challenge_or_404(db, challenge_id)
    _require_participant(challenge, current_user)
    result = await db.execute(
        select(ChallengeEvidence)
        .where(ChallengeEvidence.challenge_id == challenge_id)
        .order_by(ChallengeEvidence.created_at.desc())
    )
    return list(result.scalars().all())


@challenges_router.get("/{challenge_id}/evidence/{evidence_id}/image")
async def get_challenge_evidence_image(
    challenge_id: UUID,
    evidence_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    challenge = await _get_challenge_or_404(db, challenge_id)
    _require_participant(challenge, current_user)
    evidence = await db.get(ChallengeEvidence, evidence_id)
    if evidence is None or evidence.challenge_id != challenge_id or evidence.image_data is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الدليل غير موجود")
    return Response(content=evidence.image_data, media_type=evidence_media_type(evidence.image_path))


@challenges_router.post("/{challenge_id}/confirm", response_model=ChallengeRead)
async def confirm_challenge_result(
    challenge_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ChallengeRead:
    challenge = await _get_challenge_or_404(db, challenge_id)
    _require_participant(challenge, current_user)
    if challenge.status != ChallengeStatus.RESULT_SUBMITTED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="لا توجد نتيجة بانتظار التأكيد")
    evidence = await _latest_evidence(db, challenge.id)
    if evidence is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="لا يوجد دليل نتيجة")
    if current_user.id == evidence.submitted_by:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="لا يمكنك تأكيد نتيجتك بنفسك")
    if not await _claim_challenge_state(
        db, challenge.id, {ChallengeStatus.RESULT_SUBMITTED}, ChallengeStatus.COMPLETED
    ):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="تمت معالجة هذه النتيجة بالفعل")
    await _finalize_challenge(db, challenge, evidence.claimed_score_a, evidence.claimed_score_b)
    await record_confirmed_match(db, challenge.player_a_id, challenge.player_b_id, challenge.id)
    await db.commit()
    await db.refresh(challenge)
    return await _challenge_read(db, challenge)


@challenges_router.post("/{challenge_id}/dispute", response_model=ChallengeRead)
async def dispute_challenge_result(
    challenge_id: UUID,
    payload: DisputeCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ChallengeRead:
    challenge = await _get_challenge_or_404(db, challenge_id)
    _require_participant(challenge, current_user)
    if challenge.status != ChallengeStatus.RESULT_SUBMITTED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="لا توجد نتيجة للطعن فيها")
    evidence = await _latest_evidence(db, challenge.id)
    if evidence is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="لا يوجد دليل نتيجة")
    if current_user.id == evidence.submitted_by:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="لا يمكنك الطعن في نتيجتك بنفسك")
    if not await _claim_challenge_state(
        db, challenge.id, {ChallengeStatus.RESULT_SUBMITTED}, ChallengeStatus.DISPUTED
    ):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="تمت معالجة هذه النتيجة بالفعل")
    challenge.disputed_by = current_user.id
    await record_dispute_filed(db, current_user.id, evidence.submitted_by, challenge.id)
    await db.commit()
    await db.refresh(challenge)
    return await _challenge_read(db, challenge)


@challenges_router.post("/{challenge_id}/resolve-dispute", response_model=ChallengeRead)
async def resolve_challenge_dispute(
    challenge_id: UUID,
    payload: ResolveDispute,
    _admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> ChallengeRead:
    challenge = await _get_challenge_or_404(db, challenge_id)
    if challenge.status != ChallengeStatus.DISPUTED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="هذا التحدي ليس قيد النزاع")
    evidence = await _latest_evidence(db, challenge.id)
    submitter_was_correct = (
        evidence is not None
        and evidence.claimed_score_a == payload.score_a
        and evidence.claimed_score_b == payload.score_b
    )
    if not await _claim_challenge_state(
        db, challenge.id, {ChallengeStatus.DISPUTED}, ChallengeStatus.COMPLETED
    ):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="تم حل هذا النزاع بالفعل")
    if evidence is not None and challenge.disputed_by is not None:
        await record_dispute_resolved(
            db, evidence.submitted_by, challenge.disputed_by, submitter_was_correct,
            match_id=challenge.id, admin_id=_admin.id,
        )
    await _finalize_challenge(db, challenge, payload.score_a, payload.score_b)
    await db.commit()
    await db.refresh(challenge)
    return await _challenge_read(db, challenge)
