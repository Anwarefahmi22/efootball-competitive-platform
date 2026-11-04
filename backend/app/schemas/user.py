from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


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
    # AUD-17: no avatar_url here. Avatars change only through the
    # validated upload endpoint (POST /users/me/avatar); a free-text URL
    # field let any client bypass image validation and hotlink arbitrary
    # external images.
    bio: str | None = None
    country: str | None = None
    efootball_ign: str | None = None
    formation: str | None = Field(default=None, max_length=16)
    squad_strength: int | None = Field(default=None, ge=0, le=4000)
    # Presence privacy switch (migration 024). Lives on the User row,
    # not the profile; update_own_profile pops and applies it there.
    presence_hidden: bool | None = None


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    phone: str | None
    display_name: str
    is_active: bool
    is_verified: bool
    # Not a column on the ORM model: populated by /auth/me from the
    # is_admin database column so clients can render admin affordances
    # (the backend still authorizes every admin action independently).
    is_admin: bool = False
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
    # Presence (migration 024). last_seen_at is masked to None and
    # is_online to False while the player hides their status;
    # presence_hidden itself is the player's own setting (the profile
    # page renders its toggle from it on the owner's view).
    is_online: bool = False
    last_seen_at: datetime | None = None
    active_seconds: int = 0
    presence_hidden: bool = False


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    display_name: str = Field(min_length=2, max_length=100)

    @field_validator("password")
    @classmethod
    def _password_within_bcrypt_byte_limit(cls, value: str) -> str:
        # AUD-24: bcrypt consumes at most 72 BYTES; the character cap
        # above lets multibyte passwords pass 72 bytes and be silently
        # truncated by the hash. Reject those explicitly instead.
        if len(value.encode("utf-8")) > 72:
            raise ValueError(
                "Password is too long (maximum 72 bytes when UTF-8 encoded)"
            )
        return value


class AdminVerifyRead(BaseModel):
    """AUD-07: result of an admin verify/unverify action."""

    user_id: UUID
    display_name: str
    is_verified: bool
