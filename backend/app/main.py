import asyncio
import os
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1 import api_router, internal
from app.core.media import get_media_file, media_backend
from app.core.tournament_lifecycle import tournament_maintenance_loop
from app.db.session import get_db

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"
STORAGE_DIR = Path(__file__).resolve().parents[1] / "storage"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)


def _background_loop_enabled() -> bool:
    """The in-process maintenance loop needs a long-lived process, so it
    stays ON by default (Botkeep/Render track) and is disabled only where
    there is no process to host it — on Vercel the same sweep runs through
    the daily cron endpoint instead (ENABLE_BACKGROUND_LOOP=0)."""
    return os.environ.get("ENABLE_BACKGROUND_LOOP", "1").strip().lower() not in (
        "0",
        "false",
        "no",
    )


@asynccontextmanager
async def lifespan(_app: FastAPI):
    maintenance_task = None
    if _background_loop_enabled():
        maintenance_task = asyncio.create_task(tournament_maintenance_loop())
    try:
        yield
    finally:
        if maintenance_task is not None:
            maintenance_task.cancel()
            await asyncio.gather(maintenance_task, return_exceptions=True)


app = FastAPI(title="eFootball Competitive Platform", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")
# Mounted at the root (no /api/v1 prefix): Vercel Cron calls this exact
# path, /internal/maintenance — see app/api/v1/internal.py.
app.include_router(internal.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    return RedirectResponse(url="/auth.html")


# The API container serves the web frontend too, so a single free-tier
# service (e.g. Render) can host the whole platform with no CORS setup.
app.mount("/shared", StaticFiles(directory=FRONTEND_DIR / "shared"), name="shared")
app.mount("/landing", StaticFiles(directory=FRONTEND_DIR / "landing", html=True), name="landing")
if media_backend() == "db":
    # Vercel track: uploads live in the media_files table (the filesystem
    # is ephemeral), so /media/<id> is served from the database instead of
    # from a static directory.
    @app.get("/media/{media_id}", include_in_schema=False)
    async def serve_media_file(
        media_id: str, db: AsyncSession = Depends(get_db)
    ) -> Response:
        media = await get_media_file(db, media_id)
        if media is None:
            raise HTTPException(status_code=404, detail="Media not found")
        return Response(content=media.data, media_type=media.content_type)

else:
    app.mount("/media", StaticFiles(directory=STORAGE_DIR), name="media")
app.mount("/", StaticFiles(directory=FRONTEND_DIR / "web", html=True), name="web")
