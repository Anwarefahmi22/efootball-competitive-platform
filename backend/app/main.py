from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1 import api_router

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"

app = FastAPI(title="eFootball Competitive Platform", version="0.1.0")

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
app.mount("/", StaticFiles(directory=FRONTEND_DIR / "web", html=True), name="web")
