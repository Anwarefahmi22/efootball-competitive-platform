# Botkeep deployment — eFootball Competitive Platform

This branch (`deploy/botkeep`) adds ONLY deployment-adapter files at the
repository root. **No platform file was changed**: `backend/`, `frontend/`,
migrations and all application logic are byte-identical to `main`.

## Why these files exist

Botkeep deploys the whole repository with its own Python runtime:

- No Docker / Docker Compose, no project-root field, no install-command field.
- Dependencies are installed from a `requirements.txt` at the repository root.
- The start command is a plain process command run from the repository root.

The platform, however, is laid out for Docker: the app package and
`alembic.ini` live in `backend/`, dependencies in `backend/requirements.txt`,
and `app.main` mounts the frontend from the repository-root `frontend/`.

## Adapter files

| File | Purpose |
|---|---|
| `requirements.txt` | Root shim: `-r backend/requirements.txt` so Botkeep installs the platform's exact, unmodified dependency list. |
| `main.py` | Launcher shim: puts `backend/` on `sys.path`, chdirs there, runs `alembic upgrade head` programmatically (fails loudly if migrations fail), then serves `app.main:app` via uvicorn on `0.0.0.0:$SERVER_PORT` (fallback 8000). |
| `BOTKEEP_DEPLOY.md` | This document. |

## Botkeep server configuration

- **Runtime:** Python 3.11 (the platform's target version).
- **Start command:** `python main.py`
- **Required environment variables** (Botkeep → Environment; never commit them):
  - `DATABASE_URL` — PostgreSQL URL with the asyncpg driver, in production the
    **pooled Neon** connection string, e.g.
    `postgresql+asyncpg://<user>:<password>@<host>/<db>?sslmode=require`
    (the app's engine factory translates `sslmode` for asyncpg).
  - `JWT_SECRET_KEY` — a long random string
    (`python -c "import secrets; print(secrets.token_urlsafe(64))"`).
  - `SERVER_PORT` is injected by Botkeep; the launcher reads it automatically.
- **HTTP:** the app must be reachable via Botkeep's Domains/HTTPS routing,
  bound to the assigned `SERVER_PORT` — the launcher already binds `0.0.0.0`.

## Behaviour notes

- Migrations run on every start (same contract as the Dockerfile CMD:
  `alembic upgrade head && uvicorn ...`). If migrations fail, the process
  exits instead of serving a broken schema.
- Match evidence images are stored as bytes in the database, so they survive
  redeploys. Post/avatar images live on the local filesystem
  (`backend/storage/`, served at `/media`) — an inherited platform property,
  documented in the deployment roadmap, not changed by this adapter.
