# Vercel + Neon deployment (parallel track — branch `deploy/vercel`)

This branch adapts the platform for Vercel's serverless Python runtime
backed by the external Neon PostgreSQL project (`efootball`, Frankfurt).
It is the parallel track to the Botkeep long-running-server deployment
(branch `deploy/botkeep`); every adaptation below is additive and
env-gated, so with the flags unset the application behaves exactly as on
`main` / the Botkeep track.

## How it maps to Vercel

- `api/index.py` — the serverless entry point. It puts `backend/` on
  `sys.path` and re-exports the FastAPI `app` from `app.main`. Importing
  it runs **no migrations** and starts **no background loop**.
- `vercel.json` rewrites every request to that function, pins it to
  region **fra1** (Frankfurt — same metro as the Neon project, keeping
  function→database latency minimal) and sets `maxDuration: 60`
  (requires Fluid Compute, Vercel's default for new projects, which
  raises the Hobby-plan function ceiling from 10s to 60s).
- The static frontend needs no separate hosting: the FastAPI app itself
  mounts `frontend/` (shared/landing/web) exactly as on a server.

## Architecture deltas vs the server track

1. **Background loop → daily cron.** On a server, `lifespan` runs
   `tournament_maintenance_loop` hourly in-process. A serverless function
   has no process, so on Vercel:
   - the loop is switched off with `ENABLE_BACKGROUND_LOOP=0`
     (`ENABLE_BACKGROUND_LOOP` unset/`1` keeps the original behaviour);
   - `vercel.json` declares a daily cron (`17 3 * * *`) that calls
     `GET|POST /internal/maintenance`, which executes **one pass of the
     same** `cancel_inactive_tournaments()` function the loop wraps.
     The sweep cancels tournaments inactive for 3 days, so daily vs
     hourly cadence is not observable.
   - The endpoint requires `Authorization: Bearer <CRON_SECRET>`
     (Vercel sends this automatically when the `CRON_SECRET` env var is
     set). Unset secret → 503; wrong/missing header → 401.
2. **Media: filesystem → database.** Post/avatar uploads normally live
   in `backend/storage/` (ephemeral on Vercel). With `MEDIA_BACKEND=db`
   uploads are persisted as bytes in the new `media_files` table
   (migration `015_media_files`, same pattern as match evidence in 012),
   avatars get `/media/<id>` URLs served by a DB-backed route, and post
   images keep flowing through `GET /api/v1/posts/{id}/image`.
   With `MEDIA_BACKEND` unset (default `fs`) nothing changes.
3. **Pooled connections.** When `DATABASE_URL` points at a `-pooler`
   host, the engine is created with asyncpg `statement_cache_size=0`
   (PgBouncer transaction pooling cannot hold prepared statements).
   Direct connections are unchanged.

## Required environment variables (Vercel project settings)

| Variable | Value |
|---|---|
| `DATABASE_URL` | Neon **pooled** connection string (`...-pooler...` host, `sslmode=require`) |
| `JWT_SECRET_KEY` | strong random secret (same role as on the server track) |
| `CRON_SECRET` | strong random secret; Vercel Cron sends it as Bearer automatically |
| `ENABLE_BACKGROUND_LOOP` | `0` |
| `MEDIA_BACKEND` | `db` |

Secrets live only in the Vercel project settings — never in this repo.

## Migrations are a separate step

Functions never migrate. Before the first deploy (and after any new
migration is merged), run once from a trusted machine:

```bash
cd backend
DATABASE_URL='<neon pooled url>' JWT_SECRET_KEY='<any placeholder>' \
  alembic upgrade head
```

Expected head after this branch: `015_media_files` (16 revisions,
19 application tables including `media_files`).

## Backward compatibility statement

- Default behaviour (no new env flags) is byte-for-byte the `main`
  behaviour: loop on, filesystem media, default asyncpg caching.
- Migration `015_media_files` is purely additive (one new table, no
  altered/dropped objects) and is safe — and required — on **both**
  tracks, since the code on this branch references the `media_files`
  table only when `MEDIA_BACKEND=db`, and the Botkeep branch does not
  reference it at all.
- Existing on-disk media is ignored under `MEDIA_BACKEND=db`; the
  validation environment starts empty, which is acceptable by design.
