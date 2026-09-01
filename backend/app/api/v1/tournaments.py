from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.v1.auth import get_current_user
from app.core.bracket import generate_bracket, is_power_of_two
from app.core.economy import debit
from app.db.session import get_db
from app.models.economy import TransactionType
from app.models.tournament import Tournament, TournamentParticipant, TournamentStatus
from app.models.user import User
from app.schemas.tournament import ParticipantPublic, TournamentCreate, TournamentRead

router = APIRouter()


def _to_read(tournament: Tournament) -> TournamentRead:
    participants = [
        ParticipantPublic(
            user_id=p.user_id,
            display_name=p.user.display_name if p.user else "",
            seed=p.seed,
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
        created_by=current_user.id,
        starts_at=payload.starts_at,
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
async def get_tournament(
    tournament_id: UUID, db: AsyncSession = Depends(get_db)
) -> TournamentRead:
    tournament = await _load_tournament(db, tournament_id)
    if tournament is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tournament not found")
    return _to_read(tournament)


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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tournament is not open for registration",
        )
    if any(p.user_id == current_user.id for p in tournament.participants):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Already joined this tournament"
        )
    if len(tournament.participants) >= tournament.max_participants:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tournament is full")

    if tournament.entry_fee > 0:
        await debit(
            db, current_user.id, tournament.entry_fee, TransactionType.ENTRY_FEE,
            f"entry fee for tournament {tournament.id}",
        )
        tournament.prize_pool += tournament.entry_fee

    db.add(TournamentParticipant(tournament_id=tournament.id, user_id=current_user.id))
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
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Only the creator can start this tournament"
        )
    if tournament.status not in (
        TournamentStatus.REGISTRATION_OPEN,
        TournamentStatus.REGISTRATION_CLOSED,
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tournament cannot be started from the current status",
        )

    count = len(tournament.participants)
    if count < 2 or not is_power_of_two(count):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Participant count must be a power of 2 (at least 2) to start the bracket",
        )

    await generate_bracket(db, tournament, list(tournament.participants))
    await db.commit()
    loaded = await _load_tournament(db, tournament.id)
    assert loaded is not None
    return _to_read(loaded)
