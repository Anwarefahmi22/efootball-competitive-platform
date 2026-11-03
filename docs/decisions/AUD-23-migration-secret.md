# Decision — AUD-23: MIGRATION_SECRET, set it or leave it unset?

Status: **OWNER DECISION REQUIRED.** Current production state:
**unset** — verified during the audit; remediation changed nothing.

## What exists

`POST/GET /internal/migrate` runs Alembic migrations over HTTP,
guarded by the `MIGRATION_SECRET` environment variable
(`backend/app/api/v1/internal.py`). While the variable is unset the
endpoint fails closed: every call returns **503 "MIGRATION_SECRET is
not configured"**. The sibling endpoint `/internal/maintenance` is
guarded by Vercel Cron (`CRON_SECRET`) and is unrelated.

Separately, every migration in this remediation (020, 021) was
applied in testing through a **local Alembic run** against a scratch
database — the HTTP endpoint has never been needed.

## Option 1 — Leave it unset (recommended today)

- The endpoint stays dark; migrations run locally with
  `DATABASE_URL` pointing at the target:
  `cd backend && alembic upgrade head`.
- Attack surface: zero. There is no secret to leak, rotate, or brute
  force, and no HTTP path that can rewrite the schema.
- Cost: migrating production requires the operator (owner) to run
  one command with the production `DATABASE_URL` — which is also a
  natural checkpoint that forces a conscious decision per migration,
  exactly the posture the remediation mission mandated.

## Option 2 — Set a strong secret

- Generate ≥32 random bytes (e.g. `openssl rand -hex 32`), set
  `MIGRATION_SECRET` in the Vercel project environment, redeploy.
- Then migrations can be triggered remotely with the secret in the
  `x-migration-secret` header — convenient for CI-driven deploys.
- Obligations that come with it: store the secret only in the
  password manager + Vercel env; rotate it if it ever appears in a
  log, screenshot, or chat; treat anyone holding it as able to run
  arbitrary migrations (i.e., effectively schema-level DB access).

## Recommendation

**Option 1** while deployments are manual and rare. Revisit Option 2
only if/when a CI pipeline needs to migrate as part of an automated
deploy — at that point the secret belongs to the pipeline, is scoped
to it, and rotation is part of pipeline maintenance.
