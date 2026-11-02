from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import create_token, decode_token, hash_password, verify_password
from app.core.throttle import (
    LOGIN_EMAIL_LIMIT,
    LOGIN_IP_LIMIT,
    LOGIN_LOCK,
    LOGIN_WINDOW,
    REGISTER_IP_LIMIT,
    REGISTER_LOCK,
    REGISTER_WINDOW,
    TOO_MANY,
    clear_key,
    client_ip,
    is_locked,
    record_hit,
)
from app.db.session import get_db
from app.models.user import Profile, User
from app.schemas.auth import AccessToken, LoginRequest, RefreshRequest, TokenPair
from app.schemas.user import UserRead, UserRegister

router = APIRouter()
bearer_scheme = HTTPBearer()

# AUD-18: a real bcrypt hash of a throwaway password, verified against
# when a login names an unregistered email — the endpoint then performs
# the same expensive verification on both paths and its timing stops
# revealing which emails exist. Computed once at import.
_DUMMY_PASSWORD_HASH = hash_password("timing-equalization-dummy")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    try:
        user_id: UUID = decode_token(credentials.credentials, "access")
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    result = await db.execute(
        select(User).options(selectinload(User.profile)).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return user


@router.post("/register", response_model=TokenPair, status_code=status.HTTP_201_CREATED)
async def register(
    payload: UserRegister, request: Request, db: AsyncSession = Depends(get_db)
) -> TokenPair:
    reg_key = f"register:ip:{client_ip(request)}"
    if await is_locked(db, reg_key):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=TOO_MANY)
    await record_hit(
        db, reg_key, limit=REGISTER_IP_LIMIT, window=REGISTER_WINDOW, lock_for=REGISTER_LOCK
    )
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        display_name=payload.display_name,
    )
    user.profile = Profile()
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return TokenPair(
        access_token=create_token(user.id, "access"),
        refresh_token=create_token(user.id, "refresh"),
    )


@router.post("/login", response_model=TokenPair)
async def login(
    payload: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)
) -> TokenPair:
    email_key = f"login:email:{payload.email.lower()}"
    ip_key = f"login:ip:{client_ip(request)}"
    if await is_locked(db, email_key) or await is_locked(db, ip_key):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=TOO_MANY)
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    if user is None:
        verify_password(payload.password, _DUMMY_PASSWORD_HASH)
        password_ok = False
    else:
        password_ok = verify_password(payload.password, user.hashed_password)
    if not password_ok:
        await record_hit(
            db, email_key, limit=LOGIN_EMAIL_LIMIT, window=LOGIN_WINDOW, lock_for=LOGIN_LOCK
        )
        await record_hit(
            db, ip_key, limit=LOGIN_IP_LIMIT, window=LOGIN_WINDOW, lock_for=LOGIN_LOCK
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Inactive user")
    await clear_key(db, email_key)
    return TokenPair(
        access_token=create_token(user.id, "access"),
        refresh_token=create_token(user.id, "refresh"),
    )


@router.post("/refresh", response_model=AccessToken)
async def refresh(payload: RefreshRequest, db: AsyncSession = Depends(get_db)) -> AccessToken:
    try:
        user_id = decode_token(payload.refresh_token, "refresh")
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return AccessToken(access_token=create_token(user.id, "access"))


@router.get("/me", response_model=UserRead)
async def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user
