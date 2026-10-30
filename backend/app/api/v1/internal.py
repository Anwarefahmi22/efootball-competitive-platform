"""Internal maintenance endpoint (Vercel Cron target).

On long-running servers the tournament inactivity sweep runs as an
in-process hourly loop (see app.core.tournament_lifecycle). Serverless
functions have no long-lived process, so on Vercel the same single pass —
the exact ``cancel_inactive_tournaments()`` callable the loop wraps — is
exposed here and triggered once a day by Vercel Cron (see vercel.json).
The sweep's rule is "cancel tournaments inactive for 3 days", so a daily
cadence changes nothing observable.

Vercel Cron invokes the path with an HTTP GET and, when the CRON_SECRET
environment variable is set on the project, sends it automatically as
``Authorization: Bearer <CRON_SECRET>``. The route therefore accepts both
GET and POST and enforces that header:

- CRON_SECRET unset in the environment -> 503 (endpoint disabled)
- header missing or not matching       -> 401
- header matches                        -> 200 with a JSON summary

This router is mounted at the application root (no /api/v1 prefix) so the
path matches the cron configuration exactly: /internal/maintenance.
"""
import os
import secrets

from fastapi import APIRouter, Header, HTTPException, status

from app.core.tournament_lifecycle import cancel_inactive_tournaments

router = APIRouter()


@router.api_route("/internal/maintenance", methods=["GET", "POST"])
async def run_maintenance(
    authorization: str | None = Header(default=None),
) -> dict[str, object]:
    cron_secret = os.environ.get("CRON_SECRET")
    if not cron_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="CRON_SECRET is not configured",
        )
    expected = f"Bearer {cron_secret}"
    if authorization is None or not secrets.compare_digest(authorization, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
        )
    cancelled = await cancel_inactive_tournaments()
    return {"status": "ok", "cancelled_tournaments": cancelled}


@router.api_route("/internal/migrate", methods=["GET", "POST"])
def run_migrations(
    authorization: str | None = Header(default=None),
) -> dict[str, object]:
    """One-shot Alembic upgrade for the serverless track (deploy step).

    Long-running tracks run ``alembic upgrade head`` at process start
    (Botkeep launcher / Docker CMD). A Vercel function has no start-up
    hook under our control, so the same upgrade is exposed here as a
    guarded internal call: set ``MIGRATION_SECRET`` in the project
    environment, invoke once after (re)deploy, then remove the variable
    and the endpoint disables itself (503). The upgrade is idempotent —
    at head it is a no-op. Guard contract mirrors /internal/maintenance:
    secret unset -> 503, header mismatch -> 401, match -> run + 200.

    This handler is a plain ``def`` on purpose: Starlette runs it in a
    threadpool thread with no event loop, so Alembic's async env.py can
    drive its own ``asyncio.run`` exactly as the CLI/launcher does.
    """
    from pathlib import Path

    from alembic import command
    from alembic.config import Config

    migration_secret = os.environ.get("MIGRATION_SECRET")
    if not migration_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MIGRATION_SECRET is not configured",
        )
    expected = f"Bearer {migration_secret}"
    if authorization is None or not secrets.compare_digest(authorization, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
        )
    backend_dir = Path(__file__).resolve().parents[3]
    alembic_cfg = Config(str(backend_dir / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(backend_dir / "alembic"))
    command.upgrade(alembic_cfg, "head")
    return {"status": "ok", "migrations": "head"}
