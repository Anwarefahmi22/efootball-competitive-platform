"""Shared fixtures for the remediation test suite.

SAFETY: these tests must only ever run against a disposable PostgreSQL
database. The DSN comes from TEST_DATABASE_URL; when unset it defaults
to the local scratch cluster used during the remediation mission. The
conftest refuses to run against any DSN that does not contain "test"
or point at localhost/127.0.0.1 — production can never be a target.
"""
import os

os.environ.setdefault("JWT_SECRET_KEY", "test-only-secret")
TEST_DSN = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres@127.0.0.1:55432/arena_test",
)
assert "test" in TEST_DSN or "127.0.0.1" in TEST_DSN or "localhost" in TEST_DSN, (
    "Refusing to run tests against a non-test database URL"
)
os.environ["DATABASE_URL"] = TEST_DSN

import pytest_asyncio
from sqlalchemy import text

from app.db.session import AsyncSessionLocal, engine
from app.models.user import Profile, User

APP_TABLES = [
    "auth_throttle", "challenge_evidence", "challenge_matches", "comments",
    "follows", "groups", "match_evidence", "match_invites", "matches",
    "media_files", "player_likes", "player_ratings", "player_trust",
    "post_likes", "posts", "profiles", "seasons", "tournament_invites",
    "tournament_participants", "tournaments", "transactions", "trust_events",
    "users", "wallets", "withdrawal_requests",
]


@pytest_asyncio.fixture(autouse=True)
async def _clean_db():
    # pytest-asyncio gives every test its own event loop; pooled asyncpg
    # connections belong to the loop that opened them, so the pool is
    # disposed around each test to hand the next loop fresh connections.
    await engine.dispose()
    async with engine.begin() as conn:
        await conn.execute(
            text(f"TRUNCATE {', '.join(APP_TABLES)} RESTART IDENTITY CASCADE")
        )
    yield
    await engine.dispose()


@pytest_asyncio.fixture
async def make_user():
    from uuid import uuid4

    async def _make(db=None) -> User:
        tag = uuid4().hex[:12]
        user = User(
            email=f"tester-{tag}@example.test",
            hashed_password="not-a-real-hash",
            display_name=f"Tester {tag[:6]}",
        )
        user.profile = Profile()
        if db is None:
            async with AsyncSessionLocal() as own:
                own.add(user)
                await own.commit()
                await own.refresh(user)
                return user
        db.add(user)
        await db.flush()
        return user

    return _make
