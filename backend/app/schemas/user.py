from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    avatar_url: str | None
    bio: str | None
    country: str | None
    efootball_ign: str | None
    formation: str | None
    squad_strength: int | None
    squad_image_url: str | None
    created_at: datetime
    updated_at: datetime


class ProfileUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=2, max_length=100)
    avatar_url: str | None = None
    bio: str | None = None
    country: str | None = None
    efootball_ign: str | None = None
    formation: str | None = Field(default=None, max_length=16)
    squad_strength: int | None = Field(default=None, ge=0, le=4000)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    phone: str | None
    display_name: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime
    profile: ProfileRead | None = None


class PublicProfileRead(BaseModel):
    display_name: str
    avatar_url: str | None
    bio: str | None
    country: str | None
    efootball_ign: str | None
    formation: str | None
    squad_strength: int | None
    squad_image_url: str | None
    created_at: datetime


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    display_name: str = Field(min_length=2, max_length=100)
