"""Stage 2 — PostgreSQL concurrency tests (AUD-06, AUD-13, AUD-20, AUD-15).

These exercise the real route handlers concurrently against real
PostgreSQL (never SQLite): the races they close only exist under a
real transaction manager. Run via the suite in backend/tests with
TEST_DATABASE_URL pointing at a disposable database.
"""
import asyncio
from datetime import timedelta

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select

from app.api.v1.invites import (
    accept_match_invite,
    accept_tournament_invite,
    send_match_invite,
)
from app.api.v1.tournaments import join_tournament
from app.core import throttle
from app.db.session import AsyncSessionLocal
from app.models.auth_throttle import AuthThrottle
from app.models.invite import ChallengeMatch, MatchInvite, TournamentInvite
from app.models.tournament import Tournament, TournamentParticipant
from app.schemas.invite import MatchInviteCreate

pytestmark = pytest.mark.asyncio


async def _tournament(db, organizer, cap: int) -> Tournament:
    t = Tournament(name="Race Cup", max_participants=cap, created_by=organizer.id)
    db.add(t)
    await db.commit()
    await db.refresh(t)
    return t


async def _count(model, **where) -> int:
    async with AsyncSessionLocal() as db:
        stmt = select(func.count()).select_from(model)
        for col, val in where.items():
            stmt = stmt.where(getattr(model, col) == val)
        return await db.scalar(stmt)


# ---------------------------------------------------------------- AUD-20
async def test_record_hit_counts_every_concurrent_hit():
    key = "login:ip:203.0.113.7"

    async def hit():
        async with AsyncSessionLocal() as db:
            await throttle.record_hit(
                db, key, limit=1000,
                window=timedelta(minutes=15), lock_for=timedelta(minutes=15),
            )

    await asyncio.gather(*[hit() for _ in range(30)])
    async with AsyncSessionLocal() as db:
        row = await db.get(AuthThrottle, key)
        assert row is not None and row.fail_count == 30


async def test_record_hit_locks_at_limit_and_resets_after_window():
    key = "login:email:lock@example.test"
    for _ in range(5):
        async with AsyncSessionLocal() as db:
            await throttle.record_hit(
                db, key, limit=5,
                window=timedelta(minutes=15), lock_for=timedelta(minutes=15),
            )
    async with AsyncSessionLocal() as db:
        assert await throttle.is_locked(db, key) is True
        row = await db.get(AuthThrottle, key)
        row.window_started_at = row.window_started_at - timedelta(minutes=16)
        await db.commit()
    async with AsyncSessionLocal() as db:
        await throttle.record_hit(
            db, key, limit=5,
            window=timedelta(minutes=15), lock_for=timedelta(minutes=15),
        )
        row = await db.get(AuthThrottle, key)
        assert row.fail_count == 1
        assert await throttle.is_locked(db, key) is False


# ---------------------------------------------------------------- AUD-06
async def test_join_capacity_race_takes_last_seat_once(make_user):
    async with AsyncSessionLocal() as db:
        org = await make_user(db)
        u1 = await make_user(db)
        u2 = await make_user(db)
        t = await _tournament(db, org, cap=1)

    async def attempt(user):
        async with AsyncSessionLocal() as db:
            return await join_tournament(t.id, current_user=user, db=db)

    results = await asyncio.gather(attempt(u1), attempt(u2), return_exceptions=True)
    ok = [r for r in results if not isinstance(r, Exception)]
    errs = [r for r in results if isinstance(r, HTTPException)]
    assert len(ok) == 1
    assert len(errs) == 1 and errs[0].status_code == 400
    assert await _count(TournamentParticipant, tournament_id=t.id) == 1


async def test_tournament_invite_accept_capacity_race(make_user):
    async with AsyncSessionLocal() as db:
        org = await make_user(db)
        u1 = await make_user(db)
        u2 = await make_user(db)
        t = await _tournament(db, org, cap=1)
        inv1 = TournamentInvite(tournament_id=t.id, inviter_id=org.id, invitee_id=u1.id)
        inv2 = TournamentInvite(tournament_id=t.id, inviter_id=org.id, invitee_id=u2.id)
        db.add_all([inv1, inv2])
        await db.commit()
        await db.refresh(inv1)
        await db.refresh(inv2)

    async def attempt(invite, user):
        async with AsyncSessionLocal() as db:
            return await accept_tournament_invite(invite.id, current_user=user, db=db)

    results = await asyncio.gather(
        attempt(inv1, u1), attempt(inv2, u2), return_exceptions=True
    )
    ok = [r for r in results if not isinstance(r, Exception)]
    errs = [r for r in results if isinstance(r, HTTPException)]
    assert len(ok) == 1
    assert len(errs) == 1 and errs[0].status_code == 400
    assert await _count(TournamentParticipant, tournament_id=t.id) == 1


# ---------------------------------------------------------------- AUD-13
async def test_opposite_direction_invite_race_creates_one_pending(make_user):
    async with AsyncSessionLocal() as db:
        a = await make_user(db)
        b = await make_user(db)
        await db.commit()

    async def send(sender, target):
        async with AsyncSessionLocal() as db:
            return await send_match_invite(
                MatchInviteCreate(opponent_id=target.id), current_user=sender, db=db
            )

    results = await asyncio.gather(send(a, b), send(b, a), return_exceptions=True)
    ok = [r for r in results if not isinstance(r, Exception)]
    errs = [r for r in results if isinstance(r, HTTPException)]
    assert len(ok) == 1
    assert len(errs) == 1 and errs[0].status_code == 409
    async with AsyncSessionLocal() as db:
        pending = await db.scalar(
            select(func.count()).select_from(MatchInvite).where(
                MatchInvite.status == "pending"
            )
        )
        assert pending == 1


# ---------------------------------------------------------------- AUD-15
async def test_double_accept_creates_exactly_one_challenge(make_user):
    async with AsyncSessionLocal() as db:
        a = await make_user(db)
        b = await make_user(db)
        invite = MatchInvite(challenger_id=a.id, opponent_id=b.id)
        db.add(invite)
        await db.commit()
        await db.refresh(invite)

    async def accept():
        async with AsyncSessionLocal() as db:
            return await accept_match_invite(invite.id, current_user=b, db=db)

    results = await asyncio.gather(accept(), accept(), return_exceptions=True)
    ok = [r for r in results if not isinstance(r, Exception)]
    errs = [r for r in results if isinstance(r, HTTPException)]
    assert len(ok) == 1
    assert len(errs) == 1 and errs[0].status_code in (400, 409)
    assert await _count(ChallengeMatch, invite_id=invite.id) == 1
