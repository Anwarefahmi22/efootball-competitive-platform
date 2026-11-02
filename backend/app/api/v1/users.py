from uuid import UUID

import mimetypes
import uuid
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.v1.auth import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.core.media import (
    ALLOWED_CONTENT_TYPES,
    ALLOWED_SQUAD_CONTENT_TYPES,
    MAX_UPLOAD_BYTES,
    delete_media_db,
    media_backend,
    media_id_from_url,
    process_squad_image,
    save_avatar_image,
    save_avatar_image_db,
    save_squad_image,
    save_squad_image_db,
)
from app.schemas.user import ProfileUpdate, PublicProfileRead

router = APIRouter()
MAX_AVATAR_BYTES = 5 * 1024 * 1024


@router.get("/{user_id}", response_model=PublicProfileRead)
async def get_public_profile(user_id: UUID, db: AsyncSession = Depends(get_db)) -> PublicProfileRead:
    result = await db.execute(
        select(User).options(selectinload(User.profile)).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    profile = user.profile
    return PublicProfileRead(
        display_name=user.display_name,
        avatar_url=profile.avatar_url if profile else None,
        bio=profile.bio if profile else None,
        country=profile.country if profile else None,
        efootball_ign=profile.efootball_ign if profile else None,
        formation=profile.formation if profile else None,
        squad_strength=profile.squad_strength if profile else None,
        squad_image_url=profile.squad_image_url if profile else None,
        created_at=user.created_at,
    )


@router.patch("/me/profile", response_model=PublicProfileRead)
async def update_own_profile(
    payload: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PublicProfileRead:
    profile = current_user.profile
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    data = payload.model_dump(exclude_unset=True)
    display_name = data.pop("display_name", None)
    if display_name is not None:
        current_user.display_name = display_name.strip()
        if len(current_user.display_name) < 2:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Display name is too short")
    for field, value in data.items():
        setattr(profile, field, value)
    await db.commit()
    await db.refresh(profile)
    await db.refresh(current_user)
    return PublicProfileRead(
        display_name=current_user.display_name,
        avatar_url=profile.avatar_url,
        bio=profile.bio,
        country=profile.country,
        efootball_ign=profile.efootball_ign,
        formation=profile.formation,
        squad_strength=profile.squad_strength,
        squad_image_url=profile.squad_image_url,
        created_at=current_user.created_at,
    )


@router.post("/me/avatar", response_model=PublicProfileRead)
async def upload_avatar(
    image: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PublicProfileRead:
    content_type = image.content_type or mimetypes.guess_type(image.filename or "")[0]
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only JPEG or PNG images accepted")
    file_bytes = await image.read()
    if len(file_bytes) > MAX_AVATAR_BYTES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Avatar image exceeds 5MB limit")
    extension = ".png" if content_type == "image/png" else ".jpg"
    if media_backend() == "db":
        media_id = await save_avatar_image_db(db, file_bytes, content_type)
    else:
        save_avatar_image(str(current_user.id), file_bytes, extension)
    profile = current_user.profile
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    if media_backend() == "db":
        profile.avatar_url = f"/media/{media_id}?v={uuid.uuid4().hex}"
    else:
        profile.avatar_url = f"/media/avatars/{current_user.id}{extension}?v={uuid.uuid4().hex}"
    await db.commit()
    await db.refresh(profile)
    return PublicProfileRead(
        display_name=current_user.display_name,
        avatar_url=profile.avatar_url,
        bio=profile.bio,
        country=profile.country,
        efootball_ign=profile.efootball_ign,
        formation=profile.formation,
        squad_strength=profile.squad_strength,
        squad_image_url=profile.squad_image_url,
        created_at=current_user.created_at,
    )


@router.post("/me/squad-image", response_model=PublicProfileRead)
async def upload_squad_image(
    image: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PublicProfileRead:
    content_type = image.content_type or mimetypes.guess_type(image.filename or "")[0]
    if content_type not in ALLOWED_SQUAD_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only JPEG, PNG or WebP images accepted",
        )
    file_bytes = await image.read()
    if len(file_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Squad image exceeds 8MB limit",
        )
    try:
        webp_bytes = process_squad_image(file_bytes)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file is not a valid image",
        )
    profile = current_user.profile
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    old_media_id = media_id_from_url(profile.squad_image_url)
    if media_backend() == "db":
        media_id = await save_squad_image_db(db, webp_bytes, "image/webp")
        profile.squad_image_url = f"/media/{media_id}?v={uuid.uuid4().hex}"
        if old_media_id and old_media_id != media_id:
            await delete_media_db(db, old_media_id)
    else:
        save_squad_image(str(current_user.id), webp_bytes)
        profile.squad_image_url = f"/media/squads/{current_user.id}.webp?v={uuid.uuid4().hex}"
    await db.commit()
    await db.refresh(profile)
    return PublicProfileRead(
        display_name=current_user.display_name,
        avatar_url=profile.avatar_url,
        bio=profile.bio,
        country=profile.country,
        efootball_ign=profile.efootball_ign,
        formation=profile.formation,
        squad_strength=profile.squad_strength,
        squad_image_url=profile.squad_image_url,
        created_at=current_user.created_at,
    )


@router.delete("/me/squad-image", status_code=status.HTTP_204_NO_CONTENT)
async def delete_squad_image(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    profile = current_user.profile
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    old_media_id = media_id_from_url(profile.squad_image_url)
    profile.squad_image_url = None
    if media_backend() == "db":
        await delete_media_db(db, old_media_id)
    await db.commit()
