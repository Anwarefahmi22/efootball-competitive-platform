"""Vercel serverless entry point.

Vercel's Python runtime imports this module and serves the ASGI ``app``
exposed here. The real FastAPI application lives in ``backend/app`` (it is
shared unchanged with the Botkeep/Render long-running-server track), so all
this shim does is put ``backend/`` on ``sys.path`` and re-export the app.

Importing this module must stay side-effect free with respect to the
database: it runs NO migrations and starts NO background loop. On Vercel,
migrations are a separate deploy step (see VERCEL_DEPLOY.md) and the
hourly tournament-maintenance loop is replaced by a daily Vercel Cron hit
on ``POST /internal/maintenance`` (with ``ENABLE_BACKGROUND_LOOP=0`` set so
the lifespan handler does not try to run the loop inside a function).
"""
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.main import app  # noqa: E402

__all__ = ["app"]
