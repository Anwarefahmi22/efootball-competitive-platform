from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AccessToken(BaseModel):
    access_token: str
    token_type: str = "bearer"


class VerifyEmailRequest(BaseModel):
    email: EmailStr
    code: str = Field(min_length=4, max_length=8)


class ResendVerificationRequest(BaseModel):
    email: EmailStr


class VerificationPending(BaseModel):
    """Register response while email verification is enabled: the
    account exists but no session is issued until the code verifies."""

    verification_required: bool = True
    email: EmailStr
