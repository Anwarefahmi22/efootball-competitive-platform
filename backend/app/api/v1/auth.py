from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

import logging

from app.core.config import settings
from app.core.email_codes import CooldownActive, TooManyCodes, issue_code, verify_code
from app.core.mailer import send_verification_email
from app.core.security import (
    create_refresh_token,
    create_token,
    decode_refresh_token,
    decode_token,
    hash_password,
    token_fingerprint,
    verify_password,
)
from app.core.throttle import (
    LOGIN_IP_LIMIT,
    LOGIN_LOCK,
    LOGIN_PAIR_LIMIT,
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
from app.models.refresh_session import RefreshSession
from app.models.user import Profile, User
from app.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    ResendVerificationRequest,
    TokenPair,
    VerificationPending,
    VerifyEmailRequest,
)
from app.schemas.user import UserRead, UserRegister

logger = logging.getLogger(__name__)

router = APIRouter()
bearer_scheme = HTTPBearer()

# AUD-18: a real bcrypt hash of a throwaway password, verified against
# when a login names an unregistered email — the endpoint then performs
# the same expensive verification on both paths and its timing stops
# revealing which emails exist. Computed once at import.
_DUMMY_PASSWORD_HASH = hash_password("timing-equalization-dummy")

# AUD-10: if a rotated refresh token is replayed within this window it
# is almost certainly a second browser tab racing the first one's
# refresh, not theft — reject it, but do not nuke the family. Older
# replays revoke the whole family (see refresh()).
_REUSE_GRACE = timedelta(seconds=30)


def _refresh_expiry() -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)


async def _issue_token_pair(
    db: AsyncSession, user: User, *, family_id: UUID | None = None
) -> TokenPair:
    """Mint an access token + a tracked refresh token (AUD-10)."""
    refresh_token, jti = create_refresh_token(user.id)
    db.add(
        RefreshSession(
            id=jti,
            user_id=user.id,
            family_id=family_id or uuid4(),
            token_hash=token_fingerprint(refresh_token),
            expires_at=_refresh_expiry(),
        )
    )
    await db.commit()
    return TokenPair(
        access_token=create_token(user.id, "access"),
        refresh_token=refresh_token,
    )


async def _revoke_family(db: AsyncSession, family_id: UUID) -> None:
    await db.execute(
        update(RefreshSession)
        .where(
            RefreshSession.family_id == family_id,
            RefreshSession.revoked_at.is_(None),
        )
        .values(revoked_at=datetime.now(timezone.utc))
    )
    await db.commit()


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


async def _send_verification_code(db: AsyncSession, user: User) -> None:
    """Issue + email a fresh code. Cooldown/cap and delivery failures
    are swallowed (logged): the caller must never leak them — the user
    can always request another code from the verification screen."""
    try:
        code = await issue_code(db, user)
        await db.commit()
    except (CooldownActive, TooManyCodes):
        await db.rollback()
        return
    try:
        await send_verification_email(user.email, code)
    except Exception:
        logger.exception("verification email delivery failed")


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    payload: UserRegister, request: Request, db: AsyncSession = Depends(get_db)
):
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
    if settings.EMAIL_VERIFICATION_ENABLED:
        await _send_verification_code(db, user)
        return VerificationPending(email=user.email)
    # Verification disabled (pre-provider rollout): the account is
    # usable immediately, exactly as before the feature existed.
    user.email_verified = True
    await db.commit()
    return await _issue_token_pair(db, user)


@router.post("/login", response_model=TokenPair)
async def login(
    payload: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)
) -> TokenPair:
    # AUD-19: the per-account lock is keyed to the (email, IP) pair, so
    # an attacker can only ever lock out their own IP — never the
    # victim's. The per-IP lock still bounds total guessing per source.
    ip = client_ip(request)
    pair_key = f"login:pair:{payload.email.lower()}|{ip}"
    ip_key = f"login:ip:{ip}"
    if await is_locked(db, pair_key) or await is_locked(db, ip_key):
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
            db, pair_key, limit=LOGIN_PAIR_LIMIT, window=LOGIN_WINDOW, lock_for=LOGIN_LOCK
        )
        await record_hit(
            db, ip_key, limit=LOGIN_IP_LIMIT, window=LOGIN_WINDOW, lock_for=LOGIN_LOCK
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Inactive user")
    if settings.EMAIL_VERIFICATION_ENABLED and not user.email_verified:
        # The frontend keys off this exact detail to route the user to
        # the code-entry screen (and offer a resend) instead of an error.
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="EMAIL_NOT_VERIFIED"
        )
    await clear_key(db, pair_key)
    return await _issue_token_pair(db, user)


# The code itself burns after 5 wrong attempts (core/email_codes);
# this pair lock is only a backstop against cycling many codes, so it
# sits well above the per-code burn.
_VERIFY_PAIR_LIMIT = 20


@router.post("/verify-email", response_model=TokenPair)
async def verify_email(
    payload: VerifyEmailRequest, request: Request, db: AsyncSession = Depends(get_db)
) -> TokenPair:
    ip = client_ip(request)
    pair_key = f"verify:pair:{payload.email.lower()}|{ip}"
    if await is_locked(db, pair_key):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=TOO_MANY)
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    ok = (
        user is not None
        and not user.email_verified
        and await verify_code(db, user, payload.code)
    )
    await db.commit()
    if not ok:
        await record_hit(
            db, pair_key, limit=_VERIFY_PAIR_LIMIT, window=LOGIN_WINDOW, lock_for=LOGIN_LOCK
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="INVALID_CODE")
    await clear_key(db, pair_key)
    return await _issue_token_pair(db, user)


@router.post("/resend-verification", status_code=status.HTTP_204_NO_CONTENT)
async def resend_verification(
    payload: ResendVerificationRequest, request: Request, db: AsyncSession = Depends(get_db)
) -> None:
    # Always 204: the response must not reveal whether the email is
    # registered or already verified. Cooldown/cap apply silently.
    ip_key = f"resend:ip:{client_ip(request)}"
    if await is_locked(db, ip_key):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=TOO_MANY)
    await record_hit(
        db, ip_key, limit=REGISTER_IP_LIMIT, window=REGISTER_WINDOW, lock_for=REGISTER_LOCK
    )
    if not settings.EMAIL_VERIFICATION_ENABLED:
        return
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    if user is not None and not user.email_verified:
        await _send_verification_code(db, user)


@router.post("/refresh", response_model=TokenPair)
async def refresh(payload: RefreshRequest, db: AsyncSession = Depends(get_db)) -> TokenPair:
    """Rotate the refresh token (AUD-10).

    Every refresh mints a new refresh token in the same family and
    retires the presented one. Replaying a retired token revokes the
    whole family (theft detection), except inside a 30-second grace
    window where a racing second browser tab is the likelier cause.
    """
    try:
        user_id, jti = decode_refresh_token(payload.refresh_token)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    session = await db.get(RefreshSession, jti)
    if session is None or session.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    now = datetime.now(timezone.utc)
    if session.revoked_at is not None or session.expires_at <= now:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    if session.rotated_at is not None or session.token_hash != token_fingerprint(
        payload.refresh_token
    ):
        if session.rotated_at is None or now - session.rotated_at > _REUSE_GRACE:
            await _revoke_family(db, session.family_id)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    new_token, new_jti = create_refresh_token(user.id)
    session.rotated_at = now
    session.replaced_by_id = new_jti
    db.add(
        RefreshSession(
            id=new_jti,
            user_id=user.id,
            family_id=session.family_id,
            token_hash=token_fingerprint(new_token),
            expires_at=_refresh_expiry(),
        )
    )
    await db.commit()
    return TokenPair(
        access_token=create_token(user.id, "access"),
        refresh_token=new_token,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(payload: RefreshRequest, db: AsyncSession = Depends(get_db)) -> None:
    """Revoke the presented token's whole session family (AUD-10).

    Idempotent by design: an unknown, malformed, or already-revoked
    token still answers 204 — the client clears its storage either way.
    """
    try:
        _user_id, jti = decode_refresh_token(payload.refresh_token)
    except ValueError:
        return
    session = await db.get(RefreshSession, jti)
    if session is not None:
        await _revoke_family(db, session.family_id)


@router.get("/me", response_model=UserRead)
async def me(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> UserRead:
    # is_admin is a database column outside the ORM model (see
    # core/permissions.py); surface it so clients can show admin
    # affordances. Authorization never relies on this flag client-side.
    row = await db.execute(
        text("SELECT is_admin FROM users WHERE id = :uid"), {"uid": str(current_user.id)}
    )
    data = UserRead.model_validate(current_user)
    data.is_admin = bool(row.scalar())
    return data
