import mimetypes
import uuid as uuid_module
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import Response
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_user
from app.core.bracket import advance_winner
from app.core.league import compute_standings, is_league_complete
from app.core.permissions import get_current_admin
from app.core.rating import new_rating, new_rating_draw
from app.core.storage import ALLOWED_CONTENT_TYPES, MAX_UPLOAD_BYTES
from app.core.trust import record_confirmed_match, record_dispute_filed, record_dispute_resolved
from app.db.session import get_db
from app.models.evidence import MatchEvidence
from app.models.match import Match, MatchStatus
from app.models.rating import PlayerRating
from app.models.tournament import Tournament, TournamentFormat, TournamentStatus
from app.models.user import User
from app.schemas.evidence import DisputeCreate, EvidenceRead, ResolveDispute
from app.schemas.match import MatchRead

router = APIRouter()
tournament_matches_router = APIRouter()


async def _get_tournament(db: AsyncSession, tournament_id: UUID) -> Tournament:
    result = await db.execute(select(Tournament).where(Tournament.id == tournament_id))
    tournament = result.scalar_one_or_none()
    if tournament is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tournament not found")
    return tournament


async def _claim_match_state(
    db: AsyncSession, match_id: UUID, expected: set[MatchStatus], target: MatchStatus
) -> bool:
    """Atomically move a match out of `expected` into `target`.

    Every competitive consequence (ELO, points, goals, trust, bracket
    advancement) hangs off a match status transition, so the transition itself
    is the thing that has to happen exactly once. Reading the status in Python
    and then writing it is a check-then-act race: two concurrent requests both
    read "result_submitted", both pass the guard, and both apply the full set
    of consequences.

    A single conditional UPDATE is a compare-and-swap. Under Postgres READ
    COMMITTED the losing transaction blocks on the row lock, then re-evaluates
    the WHERE clause against the winner's committed row, finds the status has
    moved on, and updates zero rows — so exactly one caller ever gets True.
    """
    result = await db.execute(
        update(Match)
        .where(Match.id == match_id, Match.status.in_(expected))
        .values(status=target)
        .execution_options(synchronize_session=False)
    )
    return result.rowcount == 1


def _require_live_tournament(tournament: Tournament) -> None:
    """Results may only be recorded while the tournament is actually running.

    Without this a cancelled tournament keeps absorbing results: its matches
    stay playable, the confirmation applies ELO/points, and advancing the
    winner flips the tournament from CANCELLED back to COMPLETED.
    """
    if tournament.status != TournamentStatus.IN_PROGRESS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Results can only be recorded while the tournament is in progress",
        )


async def _get_or_create_rating(db: AsyncSession, user_id: UUID) -> PlayerRating:
    result = await db.execute(select(PlayerRating).where(PlayerRating.user_id == user_id))
    rating = result.scalar_one_or_none()
    if rating is None:
        rating = PlayerRating(user_id=user_id, rating=1000)
        db.add(rating)
        await db.flush()
    return rating


async def _apply_elo_win(
    db: AsyncSession, winner_id: UUID, loser_id: UUID, winner_goals: int, loser_goals: int
) -> None:
    winner = await _get_or_create_rating(db, winner_id)
    loser = await _get_or_create_rating(db, loser_id)
    # CRITICAL: capture BOTH original ratings before mutating either one.
    # Using winner.rating after it was already updated corrupts the loser's
    # calculation (breaks ELO's zero-sum symmetry).
    winner_old, loser_old = winner.rating, loser.rating
    winner.rating = new_rating(winner_old, loser_old, 1.0)
    loser.rating = new_rating(loser_old, winner_old, 0.0)
    winner.matches_played += 1
    loser.matches_played += 1
    winner.wins += 1
    loser.losses += 1
    winner.goals_for += winner_goals
    winner.goals_against += loser_goals
    loser.goals_for += loser_goals
    loser.goals_against += winner_goals
    winner.points += 3

async def _apply_elo_draw(
    db: AsyncSession, player_a_id: UUID, player_b_id: UUID, goals_a: int, goals_b: int
) -> None:
    a = await _get_or_create_rating(db, player_a_id)
    b = await _get_or_create_rating(db, player_b_id)
    a_old, b_old = a.rating, b.rating
    a.rating = new_rating_draw(a_old, b_old)
    b.rating = new_rating_draw(b_old, a_old)
    a.matches_played += 1
    b.matches_played += 1
    a.draws += 1
    b.draws += 1
    a.goals_for += goals_a
    a.goals_against += goals_b
    b.goals_for += goals_b
    b.goals_against += goals_a
    a.points += 1
    b.points += 1


async def _distribute_knockout_prize(db: AsyncSession, tournament: Tournament, winner_id: UUID) -> None:
    return


async def _distribute_league_prize_if_complete(db: AsyncSession, tournament: Tournament) -> None:
    if not await is_league_complete(db, tournament.id):
        return
    tournament.status = TournamentStatus.COMPLETED
    standings = await compute_standings(db, tournament.id)
    if standings:
        tournament.winner_id = standings[0]["user_id"]
    if not standings:
        return


async def _finalize_match(db: AsyncSession, match: Match, tournament: Tournament, score_a: int, score_b: int) -> None:
    is_league = tournament.format == TournamentFormat.LEAGUE
    is_group_match = match.group_id is not None
    draws_allowed = is_league or is_group_match

    if score_a == score_b and not draws_allowed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Draws are not allowed in this match")

    match.score_a = score_a
    match.score_b = score_b
    match.status = MatchStatus.COMPLETED
    match.completed_at = datetime.now(timezone.utc)

    if score_a == score_b:
        match.winner_id = None
        await _apply_elo_draw(db, match.player_a_id, match.player_b_id, score_a, score_b)
    else:
        winner_id = match.player_a_id if score_a > score_b else match.player_b_id
        loser_id = match.player_b_id if winner_id == match.player_a_id else match.player_a_id
        match.winner_id = winner_id
        winner_goals, loser_goals = (
            (score_a, score_b) if winner_id == match.player_a_id else (score_b, score_a)
        )
        await _apply_elo_win(db, winner_id, loser_id, winner_goals, loser_goals)

    if is_league:
        await _distribute_league_prize_if_complete(db, tournament)
    elif is_group_match:
        # Group-stage match: no bracket advancement, no prize yet — only
        # standings update via ELO above. Knockout is triggered manually
        # later via /start-knockout once the whole group stage is done.
        pass
    else:
        await advance_winner(db, match, match.winner_id)
        await _distribute_knockout_prize(db, tournament, match.winner_id)


@router.get("/{match_id}", response_model=MatchRead)
async def get_match(match_id: UUID, db: AsyncSession = Depends(get_db)) -> Match:
    result = await db.execute(select(Match).where(Match.id == match_id))
    match = result.scalar_one_or_none()
    if match is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found")
    return match


@tournament_matches_router.get("/{tournament_id}/matches", response_model=list[MatchRead])
async def list_tournament_matches(tournament_id: UUID, db: AsyncSession = Depends(get_db)) -> list[Match]:
    result = await db.execute(
        select(Match).where(Match.tournament_id == tournament_id).order_by(Match.round_number, Match.bracket_slot)
    )
    return list(result.scalars().all())


@router.post("/{match_id}/submit-result", response_model=EvidenceRead, status_code=status.HTTP_201_CREATED)
async def submit_result(
    match_id: UUID, score_a: int = Form(...), score_b: int = Form(...), image: UploadFile = File(...),
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
) -> MatchEvidence:
    result = await db.execute(select(Match).where(Match.id == match_id))
    match = result.scalar_one_or_none()
    if match is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found")
    if current_user.id not in {match.player_a_id, match.player_b_id}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only match participants can submit a result")
    if score_a < 0 or score_b < 0:
        # ResolveDispute already declares `Field(ge=0)` for the same two
        # numbers, so non-negative scores are the established domain rule;
        # a negative score would silently subtract from goals_for.
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Scores cannot be negative")
    if match.status not in {MatchStatus.READY, MatchStatus.IN_PROGRESS}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Match is not accepting a new result submission")

    tournament = await _get_tournament(db, match.tournament_id)
    _require_live_tournament(tournament)
    draws_allowed = tournament.format == TournamentFormat.LEAGUE or match.group_id is not None
    if score_a == score_b and not draws_allowed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Draws are not allowed")

    content_type = image.content_type or mimetypes.guess_type(image.filename or "")[0]
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only JPEG or PNG images are accepted")
    file_bytes = await image.read()
    if len(file_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Image exceeds 8MB limit")
    extension = ".png" if content_type == "image/png" else ".jpg"
    # Claim the transition first: two concurrent submissions must not both
    # attach evidence to the same match, because /confirm acts on the latest
    # evidence row and the losing claim would silently become the result.
    if not await _claim_match_state(
        db, match.id, {MatchStatus.READY, MatchStatus.IN_PROGRESS}, MatchStatus.RESULT_SUBMITTED
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A result has already been submitted for this match",
        )
    evidence = MatchEvidence(
        match_id=match.id, submitted_by=current_user.id, claimed_score_a=score_a, claimed_score_b=score_b,
        image_path=f"{match_id}_{uuid_module.uuid4().hex}{extension}", image_data=file_bytes,
    )
    db.add(evidence)
    match.status = MatchStatus.RESULT_SUBMITTED
    await db.commit()
    await db.refresh(evidence)
    return evidence


@router.get("/{match_id}/evidence", response_model=list[EvidenceRead])
async def list_evidence(match_id: UUID, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> list[MatchEvidence]:
    match_result = await db.execute(select(Match).where(Match.id == match_id))
    match = match_result.scalar_one_or_none()
    if match is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found")
    if current_user.id not in {match.player_a_id, match.player_b_id}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only match participants can view evidence")
    result = await db.execute(select(MatchEvidence).where(MatchEvidence.match_id == match_id).order_by(MatchEvidence.created_at.desc()))
    return list(result.scalars().all())


@router.get("/{match_id}/evidence/{evidence_id}/image")
async def get_evidence_image(match_id: UUID, evidence_id: UUID, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> Response:
    match_result = await db.execute(select(Match).where(Match.id == match_id))
    match = match_result.scalar_one_or_none()
    if match is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found")
    if current_user.id not in {match.player_a_id, match.player_b_id}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only match participants can view evidence")
    result = await db.execute(select(MatchEvidence).where(MatchEvidence.id == evidence_id, MatchEvidence.match_id == match_id))
    evidence = result.scalar_one_or_none()
    if evidence is None or evidence.image_data is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence not found")
    media_type = "image/png" if (evidence.image_path or "").endswith(".png") else "image/jpeg"
    return Response(content=evidence.image_data, media_type=media_type)


@router.post("/{match_id}/confirm", response_model=MatchRead)
async def confirm_result(match_id: UUID, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> Match:
    result = await db.execute(select(Match).where(Match.id == match_id))
    match = result.scalar_one_or_none()
    if match is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found")
    # Authorization before state: a non-participant must not be able to probe
    # this match's status or whether it has evidence attached.
    if current_user.id not in {match.player_a_id, match.player_b_id}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a match participant")
    if match.status != MatchStatus.RESULT_SUBMITTED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No pending result to confirm")
    evidence_result = await db.execute(select(MatchEvidence).where(MatchEvidence.match_id == match_id).order_by(MatchEvidence.created_at.desc()))
    evidence = evidence_result.scalars().first()
    if evidence is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No evidence found")
    if current_user.id == evidence.submitted_by:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="The submitting player cannot confirm their own result")

    tournament = await _get_tournament(db, match.tournament_id)
    _require_live_tournament(tournament)
    # One logical event -> one competitive side effect. Whichever request wins
    # this compare-and-swap is the only one that may apply ELO, points, goals,
    # trust and bracket advancement.
    if not await _claim_match_state(
        db, match.id, {MatchStatus.RESULT_SUBMITTED}, MatchStatus.COMPLETED
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="This result has already been processed"
        )
    await _finalize_match(db, match, tournament, evidence.claimed_score_a, evidence.claimed_score_b)
    await record_confirmed_match(db, match.player_a_id, match.player_b_id)
    await db.commit()
    await db.refresh(match)
    return match


@router.post("/{match_id}/dispute", response_model=MatchRead)
async def dispute_result(match_id: UUID, payload: DisputeCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> Match:
    result = await db.execute(select(Match).where(Match.id == match_id))
    match = result.scalar_one_or_none()
    if match is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found")
    # Authorization before state, same reasoning as /confirm.
    if current_user.id not in {match.player_a_id, match.player_b_id}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a match participant")
    if match.status != MatchStatus.RESULT_SUBMITTED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No pending result to dispute")
    evidence_result = await db.execute(select(MatchEvidence).where(MatchEvidence.match_id == match_id).order_by(MatchEvidence.created_at.desc()))
    evidence = evidence_result.scalars().first()
    if evidence is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No evidence found")
    if current_user.id == evidence.submitted_by:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="The submitting player cannot dispute their own result")

    # Also a compare-and-swap: a dispute filed at the same moment as the
    # opponent's confirmation must not lose the race and then record a trust
    # penalty for a result that was in fact already confirmed.
    if not await _claim_match_state(
        db, match.id, {MatchStatus.RESULT_SUBMITTED}, MatchStatus.DISPUTED
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="This result has already been processed"
        )
    match.status = MatchStatus.DISPUTED
    match.disputed_by = current_user.id
    await record_dispute_filed(db, current_user.id, evidence.submitted_by)
    await db.commit()
    await db.refresh(match)
    return match


@router.post("/{match_id}/resolve-dispute", response_model=MatchRead)
async def resolve_dispute(match_id: UUID, payload: ResolveDispute, _admin: User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)) -> Match:
    result = await db.execute(select(Match).where(Match.id == match_id))
    match = result.scalar_one_or_none()
    if match is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found")
    if match.status != MatchStatus.DISPUTED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Match is not under dispute")
    evidence_result = await db.execute(select(MatchEvidence).where(MatchEvidence.match_id == match_id).order_by(MatchEvidence.created_at.desc()))
    evidence = evidence_result.scalars().first()
    submitter_was_correct = (
        evidence is not None and evidence.claimed_score_a == payload.score_a and evidence.claimed_score_b == payload.score_b
    )

    tournament = await _get_tournament(db, match.tournament_id)
    if tournament.status == TournamentStatus.CANCELLED:
        # The competition is gone, so there is nothing to apply the outcome
        # to. Close the dispute as cancelled instead of awarding ELO, points,
        # goals and bracket advancement to a tournament that was called off —
        # which would otherwise also flip it from CANCELLED back to COMPLETED.
        match.status = MatchStatus.CANCELLED
        await db.commit()
        await db.refresh(match)
        return match
    _require_live_tournament(tournament)
    if not await _claim_match_state(
        db, match.id, {MatchStatus.DISPUTED}, MatchStatus.COMPLETED
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="This dispute has already been resolved"
        )
    if evidence is not None and match.disputed_by is not None:
        await record_dispute_resolved(db, evidence.submitted_by, match.disputed_by, submitter_was_correct)
    await _finalize_match(db, match, tournament, payload.score_a, payload.score_b)
    await db.commit()
    await db.refresh(match)
    return match
