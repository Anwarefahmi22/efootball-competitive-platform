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
    created_at: datetime
    updated_at: datetime


class ProfileUpdate(BaseModel):
    avatar_url: str | None = None
    bio: str | None = None
    country: str | None = None
    efootball_ign: str | None = None


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
    created_at: datetime


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=2, max_length=100)
