import mimetypes
import uuid as uuid_module
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_user
from app.core.bracket import advance_winner
from app.core.economy import credit
from app.core.league import compute_standings, is_league_complete
from app.core.permissions import get_current_admin
from app.core.rating import new_rating, new_rating_draw
from app.core.storage import ALLOWED_CONTENT_TYPES, MAX_UPLOAD_BYTES
from app.core.trust import record_confirmed_match, record_dispute_filed, record_dispute_resolved
from app.db.session import get_db
from app.models.economy import TransactionType
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


async def _get_or_create_rating(db: AsyncSession, user_id: UUID) -> PlayerRating:
    result = await db.execute(select(PlayerRating).where(PlayerRating.user_id == user_id))
    rating = result.scalar_one_or_none()
    if rating is None:
        rating = PlayerRating(user_id=user_id, rating=1000)
        db.add(rating)
        await db.flush()
    return rating


async def _apply_elo_win(db: AsyncSession, winner_id: UUID, loser_id: UUID) -> None:
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


async def _apply_elo_draw(db: AsyncSession, player_a_id: UUID, player_b_id: UUID) -> None:
    a = await _get_or_create_rating(db, player_a_id)
    b = await _get_or_create_rating(db, player_b_id)
    a_old, b_old = a.rating, b.rating
    a.rating = new_rating_draw(a_old, b_old)
    b.rating = new_rating_draw(b_old, a_old)
    a.matches_played += 1
    b.matches_played += 1


async def _distribute_knockout_prize(db: AsyncSession, tournament: Tournament, winner_id: UUID) -> None:
    if tournament.status == TournamentStatus.COMPLETED and not tournament.prize_distributed and tournament.prize_pool > 0:
        await credit(db, winner_id, tournament.prize_pool, TransactionType.PRIZE_PAYOUT, f"prize for winning tournament {tournament.id}")
        tournament.prize_distributed = True


async def _distribute_league_prize_if_complete(db: AsyncSession, tournament: Tournament) -> None:
    if not await is_league_complete(db, tournament.id):
        return
    tournament.status = TournamentStatus.COMPLETED
    standings = await compute_standings(db, tournament.id)
    if standings:
        tournament.winner_id = standings[0]["user_id"]
    if tournament.prize_distributed or tournament.prize_pool <= 0 or not standings:
        return
    await credit(
        db, standings[0]["user_id"], tournament.prize_pool, TransactionType.PRIZE_PAYOUT,
        f"league prize for finishing 1st in tournament {tournament.id}",
    )
    tournament.prize_distributed = True


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
        await _apply_elo_draw(db, match.player_a_id, match.player_b_id)
    else:
        winner_id = match.player_a_id if score_a > score_b else match.player_b_id
        loser_id = match.player_b_id if winner_id == match.player_a_id else match.player_a_id
        match.winner_id = winner_id
        await _apply_elo_win(db, winner_id, loser_id)

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
    if match.status not in {MatchStatus.READY, MatchStatus.IN_PROGRESS}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Match is not accepting a new result submission")

    tournament = await _get_tournament(db, match.tournament_id)
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
    if match.status != MatchStatus.RESULT_SUBMITTED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No pending result to confirm")
    evidence_result = await db.execute(select(MatchEvidence).where(MatchEvidence.match_id == match_id).order_by(MatchEvidence.created_at.desc()))
    evidence = evidence_result.scalars().first()
    if evidence is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No evidence found")
    if current_user.id not in {match.player_a_id, match.player_b_id}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a match participant")
    if current_user.id == evidence.submitted_by:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="The submitting player cannot confirm their own result")

    tournament = await _get_tournament(db, match.tournament_id)
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
    if match.status != MatchStatus.RESULT_SUBMITTED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No pending result to dispute")
    evidence_result = await db.execute(select(MatchEvidence).where(MatchEvidence.match_id == match_id).order_by(MatchEvidence.created_at.desc()))
    evidence = evidence_result.scalars().first()
    if evidence is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No evidence found")
    if current_user.id not in {match.player_a_id, match.player_b_id}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a match participant")
    if current_user.id == evidence.submitted_by:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="The submitting player cannot dispute their own result")

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
    if evidence is not None and match.disputed_by is not None:
        await record_dispute_resolved(db, evidence.submitted_by, match.disputed_by, submitter_was_correct)

    tournament = await _get_tournament(db, match.tournament_id)
    await _finalize_match(db, match, tournament, payload.score_a, payload.score_b)
    await db.commit()
    await db.refresh(match)
    return match
