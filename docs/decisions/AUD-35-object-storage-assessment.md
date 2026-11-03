# Assessment — AUD-35: Media storage, Postgres BYTEA vs object storage

Status: **DOCUMENTED — no migration proposed today.** Trigger-based
plan below. No code or infrastructure changed.

## Current design

All user media (avatars, post images, squad screenshots, match and
challenge evidence) is stored as **BYTEA rows in the `media_files`
table in PostgreSQL** when `MEDIA_BACKEND=db` (the production track),
with a filesystem backend (`MEDIA_BACKEND=fs`) for local/alternate
deployments. One module owns the whole lifecycle —
`backend/app/core/media.py` (save/read/delete for both backends, plus
the Stage 1 decode-and-normalize pipeline) — so callers never know
which backend served a file. Files are served through authenticated
or public API routes, never as raw static objects.

Sizes after the Stage 1 normalization: avatars are 512px WebP
(~10–40KB), squad screenshots ≤1600px WebP (~130KB observed), post
images ≤1600px, evidence ≤2048px q88.

## Growth math

Per completed match: ~1–2 evidence images ≈ 150–300KB. Per active
player: avatar + squad ≈ 170KB once. At 1,000 matches/month the media
table grows ≈ 0.3GB/month — years of headroom inside any realistic
Neon tier for this platform's current scale (3 real users today).
Postgres-as-file-store costs are real but deferred: backup size,
restore time, and per-query memory only bite at multi-GB media.

## Options when the trigger fires

| Option | Fit | Notes |
|---|---|---|
| Stay on Postgres | Now | Zero work; simplest operations; one backup covers data+media. |
| Cloudflare R2 | Later, likely best | S3-compatible, no egress fees (media is served often); needs signed-URL or proxy serving to preserve evidence privacy. |
| Vercel Blob | Later | Native to the current host; per-GB + operations pricing; same privacy design work. |
| AWS S3 | Later | Most standard; egress fees on every view. |

## The one design rule that must survive any move

Evidence images are **private** (participants/organizer/admins only).
Object storage must therefore serve through signed URLs minted by
the API after the existing authorization checks — never public
bucket URLs. Avatars/squads/posts may be public objects.

## Recommended triggers (any one starts the migration project)

1. `media_files` exceeds ~2GB, or the total database exceeds the
   current Neon tier's comfortable headroom.
2. Media serving becomes a measurable share of function time/billing.
3. Backup/restore time for the database becomes operationally
   painful.

## Migration shape (when triggered)

Because `core/media.py` already abstracts both backends, the move is:
add an `r2` backend behind the same functions → dual-write briefly →
backfill existing rows → flip `MEDIA_BACKEND` → drop BYTEA data in a
later migration. No API or frontend changes. Estimated effort: one
focused stage, comparable to remediation Stage 4.
