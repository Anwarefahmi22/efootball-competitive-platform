# eFootball Competitive Platform

A free competitive social platform for eFootball players: identity-first profiles, ranked play, tournaments (knockout / league / group+knockout), community, match-result verification with screenshot evidence, and a trust & fraud engine — built as a monorepo with a FastAPI backend and a future Android client.

**Tech stack:** Python 3.11+, FastAPI, PostgreSQL, SQLAlchemy 2.0 (async), Alembic, Pydantic v2, JWT auth (bcrypt) · vanilla HTML/JS web frontend · Android (Kotlin) client later.

## Status

Backend engines complete (identity, competition, verification, trust/fraud, community, seasons, analytics, group stage + knockout). The public competition model is fully free: no entry fees, deposits, withdrawals, or monetary prizes. The web frontend currently includes authentication, dashboard, tournaments, tournament details, matches and evidence, ratings, profiles, community, and Arabic/French/English language switching.

Competitive incentives are non-monetary: ELO, trust score, rankings, achievements, and competitive records. Legacy economy tables may remain for migration compatibility, but the public API does not expose financial operations.

## Run locally (Docker)

```bash
docker compose up --build
```

Then open **http://localhost:8000/** — the API container serves the web frontend itself.

- API docs: http://localhost:8000/docs
- Health: http://localhost:8000/health
- Landing page: http://localhost:8000/landing/

## Deploy free (Neon + Render)

1. **Database — [neon.tech](https://neon.tech)** (free tier): create a project and copy the connection string. Use the "pooled" connection string and append `?sslmode=require`.
2. **API + frontend — [render.com](https://render.com)** (free tier): New → Web Service → connect this GitHub repo → Runtime **Docker**, Dockerfile path `backend/Dockerfile`, root directory `/` (repo root).
3. Environment variables on Render:
   - `DATABASE_URL` = `postgresql+asyncpg://<user>:<pass>@<host>/<db>?sslmode=require` (the Neon string, driver changed to `postgresql+asyncpg`)
   - `JWT_SECRET_KEY` = a long random string (`python -c "import secrets; print(secrets.token_urlsafe(64))"`)
4. Deploy. Migrations run automatically on every start (`alembic upgrade head`), and every push to `main` redeploys.

> Free tier note: the service sleeps after ~15 minutes idle; the first request then takes ~50s while it wakes. Evidence images are stored in the database, so nothing is lost across deploys.
