import asyncio
import mimetypes
import os
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1 import api_router, internal
from app.core.config import settings
from app.core.media import get_media_file, media_backend
from app.core.tournament_lifecycle import tournament_maintenance_loop
from app.db.session import get_db

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"


def _resolve_storage_dir() -> Path:
    """Local media storage directory, created at import.

    Long-running tracks use ``backend/storage``. Serverless filesystems
    (Vercel) are read-only outside ``/tmp``, where the plain mkdir used
    to crash the whole import — fall back to ``/tmp/storage`` there.
    With MEDIA_BACKEND=db the directory is not used at runtime anyway;
    this only keeps the app importable (and fs mode functional in a
    degraded, ephemeral way) on read-only filesystems.
    """
    primary = Path(__file__).resolve().parents[1] / "storage"
    try:
        primary.mkdir(parents=True, exist_ok=True)
        return primary
    except OSError:
        fallback = Path("/tmp/storage")
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


STORAGE_DIR = _resolve_storage_dir()


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


# The interactive docs expose the full API surface; keep them off in
# production (audit 2026-11-01) and available on dev tracks via APP_ENV.
_docs_enabled = settings.APP_ENV != "production"
app = FastAPI(
    title="eFootball Competitive Platform",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if _docs_enabled else None,
    redoc_url="/redoc" if _docs_enabled else None,
    openapi_url="/openapi.json" if _docs_enabled else None,
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """422s without the submitted values.

    FastAPI's default handler echoes the offending ``input`` (which for
    the register form is the user's password) and a ``ctx`` that can
    hold non-serializable objects. The frontend only needs type/loc/msg.
    """
    errors = [
        {key: value for key, value in error.items() if key not in ("input", "ctx")}
        for error in exc.errors()
    ]
    return JSONResponse(status_code=422, content={"detail": errors})

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

# AUD-22: the security headers used to exist only in vercel.json (the
# Vercel edge). The alternate deployment track serves this app without
# them. Mirror them here — but only when the response does not already
# carry the header, so the Vercel track never emits duplicates.
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "X-Frame-Options": "DENY",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Content-Security-Policy": (
        "default-src 'self'; script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com data:; "
        "img-src 'self' data: blob: https://media.api-sports.io https://images.unsplash.com; "
        "connect-src 'self'; object-src 'none'; base-uri 'self'; "
        "form-action 'self'; frame-ancestors 'none'"
    ),
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
}


@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    for key, value in SECURITY_HEADERS.items():
        if key not in response.headers:
            response.headers[key] = value
    return response

app.include_router(api_router, prefix="/api/v1")
# Mounted at the root (no /api/v1 prefix): Vercel Cron calls this exact
# path, /internal/maintenance — see app/api/v1/internal.py.
app.include_router(internal.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    return RedirectResponse(url="/landing/")


# The API container serves the web frontend too, so a single free-tier
# service (e.g. Render) can host the whole platform with no CORS setup.
# This Python build's mime db lacks .webp, so StaticFiles served the
# logo and the landing ball as text/plain (fragile under nosniff).
mimetypes.add_type("image/webp", ".webp")

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
