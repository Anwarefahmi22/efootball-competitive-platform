"""AUD-01: migration chain integrity on a dedicated scratch database.

Creates arena_test_mig, upgrades to head, checks the Stage 2 pair
index, downgrades one step, and upgrades again. The main test database
is never touched by alembic in this module.
"""
import os
import subprocess
import sys
from pathlib import Path

import psycopg
import pytest

BACKEND = Path(__file__).resolve().parent.parent
ADMIN_DSN = "postgresql://postgres@127.0.0.1:55432/postgres"
MIG_DSN_ASYNC = "postgresql+asyncpg://postgres@127.0.0.1:55432/arena_test_mig"
HEAD = "021_refresh_sessions"
PREV = "020_fk_indexes_pair_invite"


def _alembic(*args: str) -> subprocess.CompletedProcess:
    env = dict(os.environ, JWT_SECRET_KEY="mig-test", DATABASE_URL=MIG_DSN_ASYNC)
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=BACKEND, env=env, capture_output=True, text=True, timeout=600,
    )


@pytest.fixture(scope="module")
def mig_db():
    with psycopg.connect(ADMIN_DSN, autocommit=True) as conn:
        conn.execute("DROP DATABASE IF EXISTS arena_test_mig")
        conn.execute("CREATE DATABASE arena_test_mig")
    yield
    with psycopg.connect(ADMIN_DSN, autocommit=True) as conn:
        conn.execute("DROP DATABASE IF EXISTS arena_test_mig")


def _current_revision() -> str:
    with psycopg.connect(
        "postgresql://postgres@127.0.0.1:55432/arena_test_mig"
    ) as conn:
        row = conn.execute("SELECT version_num FROM alembic_version").fetchone()
        return row[0]


def test_full_chain_upgrade_downgrade_upgrade(mig_db):
    up = _alembic("upgrade", "head")
    assert up.returncode == 0, up.stderr[-2000:]
    assert _current_revision() == HEAD

    with psycopg.connect(
        "postgresql://postgres@127.0.0.1:55432/arena_test_mig"
    ) as conn:
        row = conn.execute(
            "SELECT indexdef FROM pg_indexes WHERE indexname = 'uq_match_invite_pending_pair'"
        ).fetchone()
        assert row is not None and "LEAST" in row[0]
        fk_indexes = conn.execute(
            "SELECT count(*) FROM pg_indexes WHERE indexname LIKE 'ix_%'"
        ).fetchone()[0]
        assert fk_indexes >= 19

    down = _alembic("downgrade", "-1")
    assert down.returncode == 0, down.stderr[-2000:]
    assert _current_revision() == PREV

    up2 = _alembic("upgrade", "head")
    assert up2.returncode == 0, up2.stderr[-2000:]
    assert _current_revision() == HEAD
