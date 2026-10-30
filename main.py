"""Botkeep deployment launcher for the eFootball Competitive Platform.

Botkeep deploys the whole repository with its own Python runtime:
no Docker, no project-root field, no install-command field, and the
default start command is literally ``python main.py`` run from the
repository root. The platform itself lives in ``backend/`` and expects
to run from there (``alembic.ini`` and the ``app`` package), while
``app.main`` mounts the web frontend from the repository-root
``frontend/`` directory.

This shim bridges the two layouts WITHOUT touching any platform file:

1. Resolve the repository root from ``__file__``.
2. Put ``backend/`` on ``sys.path`` and chdir into it, so ``app`` and
   ``alembic.ini`` resolve exactly as they do in the Docker layout.
3. Run ``alembic upgrade head`` programmatically; abort loudly if the
   migrations fail (same fail-fast contract as the Dockerfile CMD).
4. Serve ``app.main:app`` with uvicorn on ``0.0.0.0:$SERVER_PORT``
   (Botkeep injects ``SERVER_PORT``; 8000 is the local fallback).

Required environment variables (set in Botkeep's Environment panel,
never committed): ``DATABASE_URL`` (``postgresql+asyncpg://...``) and
``JWT_SECRET_KEY``.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
BACKEND_DIR = REPO_ROOT / "backend"


def _require_env() -> None:
    missing = [name for name in ("DATABASE_URL", "JWT_SECRET_KEY") if not os.environ.get(name)]
    if missing:
        raise SystemExit(
            "FATAL: required environment variable(s) not set: " + ", ".join(missing)
        )


def _run_migrations() -> None:
    from alembic import command
    from alembic.config import Config

    alembic_cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    # alembic.ini uses a relative script_location; pin it absolutely so
    # resolution never depends on the caller's working directory.
    alembic_cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    print("[botkeep-launcher] Running: alembic upgrade head", flush=True)
    command.upgrade(alembic_cfg, "head")
    print("[botkeep-launcher] Migrations applied successfully.", flush=True)


def main() -> None:
    _require_env()

    sys.path.insert(0, str(BACKEND_DIR))
    os.chdir(BACKEND_DIR)

    _run_migrations()

    import uvicorn

    port = int(os.environ.get("SERVER_PORT", "8000"))
    print(f"[botkeep-launcher] Starting uvicorn on 0.0.0.0:{port}", flush=True)
    uvicorn.run("app.main:app", host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
