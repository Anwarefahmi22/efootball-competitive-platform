from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.v1.auth import get_current_user
from app.core.bracket import assign_random_seeds, build_bracket_matches, is_power_of_two
from app.core.economy import credit, debit
from app.core.league import compute_standings, generate_league_schedule
from app.db.session import get_db
from app.models.economy import TransactionType
from app.models.tournament import Tournament, TournamentFormat, TournamentParticipant, TournamentStatus
from app.models.user import User
from app.schemas.league import StandingRow
from app.schemas.tournament import ParticipantPublic, TournamentCreate, TournamentRead

router = APIRouter()


def _to_read(tournament: Tournament) -> TournamentRead:
    participants = [
        ParticipantPublic(
            user_id=p.user_id,
            display_name=p.user.display_name if p.user else "",
            seed=p.seed,
            status=p.status,
        )
        for p in tournament.participants
    ]
    return TournamentRead(
        id=tournament.id,
        name=tournament.name,
        description=tournament.description,
        format=tournament.format,
        status=tournament.status,
        max_participants=tournament.max_participants,
        entry_fee=tournament.entry_fee,
        prize_pool=tournament.prize_pool,
        draw_completed=tournament.draw_completed,
        requires_approval=tournament.requires_approval,
        season_id=tournament.season_id,
        created_by=tournament.created_by,
        starts_at=tournament.starts_at,
        created_at=tournament.created_at,
        updated_at=tournament.updated_at,
        participant_count=len(tournament.participants),
        participants=participants,
    )


async def _load_tournament(db: AsyncSession, tournament_id: UUID) -> Tournament | None:
    result = await db.execute(
        select(Tournament)
        .options(selectinload(Tournament.participants).selectinload(TournamentParticipant.user))
        .where(Tournament.id == tournament_id)
    )
    return result.scalar_one_or_none()


def _approved(tournament: Tournament) -> list[TournamentParticipant]:
    return [p for p in tournament.participants if p.status == "approved"]


async def _refund_and_remove(db: AsyncSession, tournament: Tournament, participant: TournamentParticipant) -> None:
    if tournament.entry_fee > 0:
        await credit(
            db, participant.user_id, tournament.entry_fee, TransactionType.ENTRY_FEE_REFUND,
            f"refund for leaving/rejected from tournament {tournament.id}",
        )
        tournament.prize_pool = max(0, tournament.prize_pool - tournament.entry_fee)
    await db.delete(participant)


@router.post("", response_model=TournamentRead, status_code=status.HTTP_201_CREATED)
async def create_tournament(
    payload: TournamentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TournamentRead:
    if payload.entry_fee < 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="entry_fee cannot be negative")
    tournament = Tournament(
        name=payload.name,
        description=payload.description,
        format=payload.format,
        status=TournamentStatus.REGISTRATION_OPEN,
        max_participants=payload.max_participants,
        entry_fee=payload.entry_fee,
        prize_pool=0,
        requires_approval=payload.requires_approval,
        created_by=current_user.id,
        starts_at=payload.starts_at,
        season_id=payload.season_id,
    )
    db.add(tournament)
    await db.commit()
    loaded = await _load_tournament(db, tournament.id)
    assert loaded is not None
    return _to_read(loaded)


@router.get("", response_model=list[TournamentRead])
async def list_tournaments(
    status_filter: TournamentStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> list[TournamentRead]:
    stmt = (
        select(Tournament)
        .options(selectinload(Tournament.participants).selectinload(TournamentParticipant.user))
        .order_by(Tournament.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    if status_filter is not None:
        stmt = stmt.where(Tournament.status == status_filter)
    result = await db.execute(stmt)
    return [_to_read(t) for t in result.scalars().unique().all()]


@router.get("/{tournament_id}", response_model=TournamentRead)
async def get_tournament(tournament_id: UUID, db: AsyncSession = Depends(get_db)) -> TournamentRead:
    tournament = await _load_tournament(db, tournament_id)
    if tournament is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tournament not found")
    return _to_read(tournament)


@router.patch("/{tournament_id}", response_model=TournamentRead)
async def update_tournament(
    tournament_id: UUID,
    name: str | None = None,
    description: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TournamentRead:
    tournament = await _load_tournament(db, tournament_id)
    if tournament is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tournament not found")
    if tournament.created_by != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the creator can edit this tournament")
    if tournament.status not in (TournamentStatus.REGISTRATION_OPEN, TournamentStatus.REGISTRATION_CLOSED):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot edit a tournament once it has started")
    if name is not None:
        tournament.name = name
    if description is not None:
        tournament.description = description
    await db.commit()
    loaded = await _load_tournament(db, tournament.id)
    assert loaded is not None
    return _to_read(loaded)


@router.post("/{tournament_id}/cancel", response_model=TournamentRead)
async def cancel_tournament(
    tournament_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TournamentRead:
    tournament = await _load_tournament(db, tournament_id)
    if tournament is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tournament not found")
    if tournament.created_by != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the creator can cancel this tournament")
    if tournament.status in (TournamentStatus.COMPLETED, TournamentStatus.CANCELLED):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tournament already finished or cancelled")

    for participant in list(tournament.participants):
        await _refund_and_remove(db, tournament, participant)
    tournament.status = TournamentStatus.CANCELLED
    await db.commit()
    loaded = await _load_tournament(db, tournament.id)
    assert loaded is not None
    return _to_read(loaded)


@router.get("/{tournament_id}/standings", response_model=list[StandingRow])
async def get_standings(tournament_id: UUID, db: AsyncSession = Depends(get_db)) -> list[StandingRow]:
    tournament = await _load_tournament(db, tournament_id)
    if tournament is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tournament not found")
    if tournament.format != TournamentFormat.LEAGUE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Standings only apply to league tournaments")
    rows = await compute_standings(db, tournament_id)
    return [StandingRow(**r) for r in rows]


@router.post("/{tournament_id}/join", response_model=TournamentRead)
async def join_tournament(
    tournament_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TournamentRead:
    tournament = await _load_tournament(db, tournament_id)
    if tournament is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tournament not found")
    if tournament.status != TournamentStatus.REGISTRATION_OPEN:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tournament is not open for registration")
    if any(p.user_id == current_user.id for p in tournament.participants):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Already joined this tournament")
    if len(tournament.participants) >= tournament.max_participants:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tournament is full")

    if tournament.entry_fee > 0:
        await debit(
            db, current_user.id, tournament.entry_fee, TransactionType.ENTRY_FEE,
            f"entry fee for tournament {tournament.id}",
        )
        tournament.prize_pool += tournament.entry_fee

    initial_status = "pending" if tournament.requires_approval else "approved"
    db.add(TournamentParticipant(tournament_id=tournament.id, user_id=current_user.id, status=initial_status))
    await db.commit()
    loaded = await _load_tournament(db, tournament.id)
    assert loaded is not None
    return _to_read(loaded)


@router.post("/{tournament_id}/leave", response_model=TournamentRead)
async def leave_tournament(
    tournament_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TournamentRead:
    tournament = await _load_tournament(db, tournament_id)
    if tournament is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tournament not found")
    if tournament.status != TournamentStatus.REGISTRATION_OPEN:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot leave after registration has closed")

    participant = next((p for p in tournament.participants if p.user_id == current_user.id), None)
    if participant is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You are not registered in this tournament")

    await _refund_and_remove(db, tournament, participant)
    await db.commit()
    loaded = await _load_tournament(db, tournament.id)
    assert loaded is not None
    return _to_read(loaded)


@router.post("/{tournament_id}/participants/{user_id}/approve", response_model=TournamentRead)
async def approve_participant(
    tournament_id: UUID,
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TournamentRead:
    tournament = await _load_tournament(db, tournament_id)
    if tournament is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tournament not found")
    if tournament.created_by != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the creator can approve participants")

    participant = next((p for p in tournament.participants if p.user_id == user_id), None)
    if participant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Participant not found")
    if participant.status != "pending":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Participant is not pending approval")

    participant.status = "approved"
    await db.commit()
    loaded = await _load_tournament(db, tournament.id)
    assert loaded is not None
    return _to_read(loaded)


@router.post("/{tournament_id}/participants/{user_id}/reject", response_model=TournamentRead)
async def reject_participant(
    tournament_id: UUID,
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TournamentRead:
    tournament = await _load_tournament(db, tournament_id)
    if tournament is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tournament not found")
    if tournament.created_by != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the creator can reject participants")
    if tournament.status != TournamentStatus.REGISTRATION_OPEN:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot reject after registration has closed")

    participant = next((p for p in tournament.participants if p.user_id == user_id), None)
    if participant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Participant not found")

    await _refund_and_remove(db, tournament, participant)
    await db.commit()
    loaded = await _load_tournament(db, tournament.id)
    assert loaded is not None
    return _to_read(loaded)


@router.post("/{tournament_id}/draw", response_model=TournamentRead)
async def draw_tournament(
    tournament_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TournamentRead:
    tournament = await _load_tournament(db, tournament_id)
    if tournament is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tournament not found")
    if tournament.created_by != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the creator can perform the draw")
    if tournament.draw_completed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Draw already performed")
    if tournament.status != TournamentStatus.REGISTRATION_OPEN:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Draw can only be performed while registration is open")

    approved = _approved(tournament)
    count = len(approved)
    if tournament.format == TournamentFormat.SINGLE_ELIMINATION:
        if count < 2 or not is_power_of_two(count):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Approved participant count must be a power of 2 (at least 2) to draw",
            )
    else:
        if count < 2:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Need at least 2 approved participants to draw")

    assign_random_seeds(approved)
    tournament.status = TournamentStatus.REGISTRATION_CLOSED
    tournament.draw_completed = True
    await db.commit()
    loaded = await _load_tournament(db, tournament.id)
    assert loaded is not None
    return _to_read(loaded)


@router.post("/{tournament_id}/start", response_model=TournamentRead)
async def start_tournament(
    tournament_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TournamentRead:
    tournament = await _load_tournament(db, tournament_id)
    if tournament is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tournament not found")
    if tournament.created_by != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the creator can start this tournament")
    if not tournament.draw_completed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The draw must be performed first — call /draw before /start")
    if tournament.status != TournamentStatus.REGISTRATION_CLOSED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tournament cannot be started from the current status")

    approved = _approved(tournament)
    if tournament.format == TournamentFormat.LEAGUE:
        await generate_league_schedule(db, tournament, approved)
        tournament.status = TournamentStatus.IN_PROGRESS
    else:
        await build_bracket_matches(db, tournament, approved)

    await db.commit()
    loaded = await _load_tournament(db, tournament.id)
    assert loaded is not None
    return _to_read(loaded)
