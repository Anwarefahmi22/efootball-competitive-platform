from datetime import timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.v1.auth import get_current_user
from app.core.media import (
    MAX_UPLOAD_BYTES,
    delete_media_db,
    get_media_file,
    is_media_ref,
    media_backend,
    media_ref,
    normalize_image,
    parse_media_ref,
    read_upload_limited,
    save_post_image,
    save_post_image_db,
)
from app.core.permissions import is_admin
from app.core.rooms import delete_room_and_media
from app.core.throttle import enforce_quota
from app.db.session import get_db
from app.models.room import RoomMessage, TournamentRoom
from app.models.tournament import Tournament, TournamentParticipant
from app.models.user import User
from app.schemas.room import RoomMessageRead, RoomRead

router = APIRouter()


async def _load_tournament(db: AsyncSession, tournament_id: UUID) -> Tournament:
    result = await db.execute(select(Tournament).where(Tournament.id == tournament_id))
    tournament = result.scalar_one_or_none()
    if tournament is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tournament not found")
    return tournament


async def _load_room(db: AsyncSession, tournament_id: UUID) -> TournamentRoom | None:
    result = await db.execute(
        select(TournamentRoom).where(TournamentRoom.tournament_id == tournament_id)
    )
    return result.scalar_one_or_none()


async def _member_count(db: AsyncSession, tournament_id: UUID) -> int:
    result = await db.execute(
        select(func.count())
        .select_from(TournamentParticipant)
        .where(
            TournamentParticipant.tournament_id == tournament_id,
            TournamentParticipant.status == "approved",
        )
    )
    return result.scalar_one()


async def _is_member(db: AsyncSession, tournament: Tournament, user_id: UUID) -> bool:
    if tournament.created_by == user_id:
        return True
    result = await db.execute(
        select(TournamentParticipant.id).where(
            TournamentParticipant.tournament_id == tournament.id,
            TournamentParticipant.user_id == user_id,
            TournamentParticipant.status == "approved",
        )
    )
    return result.scalar_one_or_none() is not None


async def _build_room_read(
    db: AsyncSession, tournament: Tournament, user: User
) -> RoomRead:
    room = await _load_room(db, tournament.id)
    return RoomRead(
        exists=room is not None,
        room_id=room.id if room else None,
        tournament_id=tournament.id,
        is_member=await _is_member(db, tournament, user.id),
        is_organizer=tournament.created_by == user.id,
        member_count=await _member_count(db, tournament.id),
        created_at=room.created_at if room else None,
    )


async def _require_room_member(
    db: AsyncSession, tournament_id: UUID, user: User
) -> tuple[Tournament, TournamentRoom]:
    tournament = await _load_tournament(db, tournament_id)
    room = await _load_room(db, tournament_id)
    if room is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="This tournament has no group")
    if not await _is_member(db, tournament, user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only tournament members can access its group",
        )
    return tournament, room


def _to_message_read(message: RoomMessage, *, can_delete: bool) -> RoomMessageRead:
    author = message.author
    return RoomMessageRead(
        id=message.id,
        author_id=message.author_id,
        author_name=author.display_name if author else "",
        author_avatar_url=author.profile.avatar_url if author and author.profile else None,
        body=message.body,
        has_image=message.image_path is not None,
        can_delete=can_delete,
        created_at=message.created_at,
    )


@router.get("/{tournament_id}/room", response_model=RoomRead)
async def get_room(
    tournament_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RoomRead:
    tournament = await _load_tournament(db, tournament_id)
    return await _build_room_read(db, tournament, current_user)


@router.post("/{tournament_id}/room", response_model=RoomRead, status_code=status.HTTP_201_CREATED)
async def create_room(
    tournament_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RoomRead:
    tournament = await _load_tournament(db, tournament_id)
    if tournament.created_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the tournament creator can create its group",
        )
    if await _load_room(db, tournament_id) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="This tournament already has a group"
        )
    room = TournamentRoom(tournament_id=tournament.id, created_by=current_user.id)
    db.add(room)
    await db.commit()
    return await _build_room_read(db, tournament, current_user)


@router.delete("/{tournament_id}/room", status_code=status.HTTP_204_NO_CONTENT)
async def delete_room(
    tournament_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    tournament = await _load_tournament(db, tournament_id)
    if tournament.created_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the tournament creator can delete its group",
        )
    room = await _load_room(db, tournament_id)
    if room is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="This tournament has no group")
    await delete_room_and_media(db, room)
    await db.commit()


@router.get("/{tournament_id}/room/messages", response_model=list[RoomMessageRead])
async def list_messages(
    tournament_id: UUID,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[RoomMessageRead]:
    tournament, room = await _require_room_member(db, tournament_id, current_user)
    result = await db.execute(
        select(RoomMessage)
        .options(selectinload(RoomMessage.author).selectinload(User.profile))
        .where(RoomMessage.room_id == room.id)
        .order_by(RoomMessage.created_at.desc(), RoomMessage.id.desc())
        .limit(limit)
        .offset(offset)
    )
    messages = list(result.scalars().all())
    messages.reverse()
    admin = await is_admin(db, current_user.id)
    return [
        _to_message_read(
            m,
            can_delete=(
                m.author_id == current_user.id
                or tournament.created_by == current_user.id
                or admin
            ),
        )
        for m in messages
    ]


@router.post(
    "/{tournament_id}/room/messages",
    response_model=RoomMessageRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_message(
    tournament_id: UUID,
    body: str | None = Form(default=None, max_length=2000),
    image: UploadFile | None = File(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RoomMessageRead:
    tournament, room = await _require_room_member(db, tournament_id, current_user)
    await enforce_quota(
        db,
        f"quota:room_message:{current_user.id}",
        limit=120,
        window=timedelta(hours=1),
        lock_for=timedelta(hours=1),
    )
    if body is not None and not body.strip():
        body = None
    if not body and not image:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message must have text or a photo",
        )
    image_path = None
    if image is not None:
        # Same pipeline as post photos: capped stream, decode-verify,
        # re-encode to WebP — the declared content type is never trusted.
        raw_bytes = await read_upload_limited(image, MAX_UPLOAD_BYTES)
        try:
            file_bytes = normalize_image(raw_bytes, max_width=1600)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The uploaded file is not a valid image",
            )
        if media_backend() == "db":
            media_id = await save_post_image_db(db, file_bytes, "image/webp")
            image_path = media_ref(media_id)
        else:
            image_path = save_post_image(file_bytes, ".webp")
    message = RoomMessage(
        room_id=room.id, author_id=current_user.id, body=body, image_path=image_path
    )
    db.add(message)
    await db.commit()
    loaded = (
        await db.execute(
            select(RoomMessage)
            .options(selectinload(RoomMessage.author).selectinload(User.profile))
            .where(RoomMessage.id == message.id)
        )
    ).scalar_one()
    return _to_message_read(loaded, can_delete=True)


@router.get("/{tournament_id}/room/messages/{message_id}/image")
async def get_message_image(
    tournament_id: UUID,
    message_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _, room = await _require_room_member(db, tournament_id, current_user)
    result = await db.execute(
        select(RoomMessage).where(
            RoomMessage.id == message_id, RoomMessage.room_id == room.id
        )
    )
    message = result.scalar_one_or_none()
    if message is None or message.image_path is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")
    if is_media_ref(message.image_path):
        media = await get_media_file(db, parse_media_ref(message.image_path))
        if media is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")
        return Response(content=media.data, media_type=media.content_type)
    return FileResponse(message.image_path)


@router.delete(
    "/{tournament_id}/room/messages/{message_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_message(
    tournament_id: UUID,
    message_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    tournament, room = await _require_room_member(db, tournament_id, current_user)
    result = await db.execute(
        select(RoomMessage).where(
            RoomMessage.id == message_id, RoomMessage.room_id == room.id
        )
    )
    message = result.scalar_one_or_none()
    if message is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
    if (
        message.author_id != current_user.id
        and tournament.created_by != current_user.id
        and not await is_admin(db, current_user.id)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the author, the tournament creator, or an admin can delete this message",
        )
    if message.image_path and is_media_ref(message.image_path):
        await delete_media_db(db, parse_media_ref(message.image_path))
    await db.delete(message)
    await db.commit()
