# eFootball Arena — Remediation Tracking Document

Mission: Comprehensive Remediation & Production Hardening (authorized 2026-11-03).
Authoritative findings source: **eFootball Arena — Comprehensive Technical Audit Report, 3 November 2026** (0 P0 · 2 P1 · 12 P2 · 20 P3).
This document is the Stage 0 baseline + the AUD-01…AUD-35 implementation map. It is updated at the end of every stage.

---

## 1. Verified repository baseline (Stage 0, 2026-11-03)

| Item | Verified value |
|---|---|
| Production URL | https://efootballarena-app.vercel.app |
| Production branch | `deploy/vercel` |
| Production commit | `b7350af2e06b` (GitHub API ref check, re-verified at Stage 0) |
| Working tree | Byte-identical to production for all sampled files (SHA-256: theme.css, landing, dashboard, arena-star, auth, i18n.js — audit §2, still valid at Stage 0) |
| Remediation branch | `remediation/audit-2026-11-03`, forked from `b7350af2e06b` (this document is its first commit). Production branch is never modified directly. |
| Migration head | `019_invites_challenges` — chain linear, single head (001 → … → 012 → 013_free_competition → 013_global_standings → 014_trust_events → 015_media_files → 016_auth_throttle → 017_arena_star → 018_squad_image → 019). Next migration: **020**. |
| Deployment config | `vercel.json`: single function `api/index.py` (fra1, maxDuration 60, includeFiles frontend/** + backend/alembic/**), catch-all rewrite, daily cron 03:17 UTC → `/internal/maintenance`, edge security headers incl. CSP. FastAPI serves the frontend (same-origin). |
| Dependencies | Root `requirements.txt` ≡ `backend/requirements.txt` (diff-verified). Both must stay in sync after any dependency change. |
| Backend shape | FastAPI, 16 API modules, **77 `/api/v1` method-path pairs**, 85 registered routes total. |
| Database shape | 21 live model tables + 3 dead economy tables (transactions, wallets, withdrawal_requests — AUD-29, deferred). |

### Branch map (26 branches, GitHub API census at Stage 0)

| Branch | Head | Role |
|---|---|---|
| `deploy/vercel` | b7350af2e06b | **PRODUCTION source of truth.** Never commit remediation work here directly. |
| `deploy/botkeep` | 6abf72aa31dd | Alternate long-running deployment track (Render/Botkeep). Not production today; several audit findings (AUD-11, AUD-22) concern this track specifically. |
| `main` | 2d89573f1313 | GitHub default branch; stale PR line; **not** a deployment source. Do not base work on it. |
| `remediation/audit-2026-11-03` | (this branch) | The remediation mission branch, based on `deploy/vercel@b7350af2`. |
| `arena/*` (3) | various | Arena AI working branches — never delete (mission rule). |
| `phase*`, `feat/*`, `critical-fixes-round1`, `high-priority-fixes-round2`, `push-compose`, `anwarefahmi22-repo-analysis` | various | Historical development lines. No merges into the remediation branch (unrelated histories). |

Local-clone note (AUD-30): the pre-existing local `.git` HEAD sits on a divergent historical line because deployments were pushed via the GitHub Git Data API. The **GitHub branch `deploy/vercel` is the only source of truth**; the remediation working tree was verified against it by content hash, and all remediation commits are made through the same API flow onto the remediation branch.

### Baseline automated checks (Stage 0, re-run and recorded)

| Check | Result |
|---|---|
| Python compilation (`compileall backend/app`) | OK |
| App import + route inventory | OK — 85 routes, 77 `/api/v1` pairs |
| ELO baseline (1000v1000 win/loss/draw) | OK — 1016 / 984 / 1000 |
| Pyflakes (`backend/app`) | 10 findings (unused imports + string-only model references — AUD-31) |
| JS syntax (5 shared files, `node --check`) | OK — 5/5 (inline blocks 14/14 verified in audit) |
| Requirements sync | OK |
| Migration chain | OK — linear, head 019 |

### Environment capabilities (this workstation)

- Python 3.12.3, Node v24.22.1 available.
- **No Docker. No local PostgreSQL.** → Testcontainers is impossible locally; AUD-01/Stage 2–3 PostgreSQL tests need one of:
  1. **GitHub Actions service container** (postgres image) — tests run in CI; zero local infra. Recommended as the canonical gate.
  2. **Disposable Neon branch** of the production project (copy-on-write, deleted after use) — isolated from production data, but lives inside the production project; use only with explicit owner awareness at Stage 2/3 kickoff.
  3. **Standalone PostgreSQL binaries** downloaded into the workstation (EDB tarball via proxy) — self-contained; to be verified at Stage 3 setup.
- Production database is **never** a test target.

### Conflicts between the audit report and the current repository

None. Every audited claim re-verified at Stage 0 (branch head, migration head, route counts, file hashes) matches the audit report. One clarification, not a conflict: the audit's route count (85 total / 77 `/api/v1`) counts method-path pairs on the imported app; the security slice's matrix counted 83 method-routes excluding static mounts — same inventory, different convention.

---

## 2. Approval gates (mission §1.3 — always in force)

Prohibited without explicit owner approval: production deployment; production migrations; production data deletion/modification; real production matches or rating changes; production secret/env changes; dropping economy tables; public/private access-policy changes (AUD-14, AUD-26); automated penalties from collusion signals (AUD-28).

Everything in Stages 1–6 is code + tests on the remediation branch only. Stage 7 items are proposals/runbooks, never executions.

---

## 3. Implementation map — AUD-01 … AUD-35

Status vocabulary: NOT STARTED · IN PROGRESS · FIXED AND VERIFIED · FIXED BUT NOT FULLY VERIFIED · BLOCKED · OWNER DECISION REQUIRED · DEFERRED.

| ID | Sev | Stage | Primary files / modules | Migration | Status |
|---|---|---|---|---|---|
| AUD-01 | P1 | 3 | `backend/tests/` (new), `.github/workflows/ci.yml` (new), `backend/app/**` (subjects) | — | NOT STARTED |
| AUD-02 | P1 | 7 | Runbook in final decisions pack (operations only) | — | OWNER DECISION REQUIRED |
| AUD-03 | P2 | 6 | `backend/app/api/v1/players.py`, `backend/app/schemas/player.py`, `frontend/web/app/arena-star.html` | — | NOT STARTED |
| AUD-04 | P2 | 2 | `backend/alembic/versions/020_*.py` (new) | **020** | NOT STARTED |
| AUD-05 | P2 | 6 | `backend/app/api/v1/invites.py` (`_brief`, inbox, challenge reads) | — | NOT STARTED |
| AUD-06 | P2 | 2 | `backend/app/api/v1/tournaments.py` (join), `backend/app/api/v1/invites.py` (tournament accept) | — | NOT STARTED |
| AUD-07 | P2 | 5 | `backend/app/api/v1/admin.py`, `backend/app/schemas/admin.py` (verify schemas), `frontend/web/app/admin.html` | — (is_verified column exists) | NOT STARTED |
| AUD-08 | P2 | 5 | `backend/app/api/v1/posts.py`, `frontend/web/app/community.html` | — (cascades exist) | NOT STARTED |
| AUD-09 | P2 | 1 | `frontend/web/app/invites.html` (error render paths ~L157, L184–191) | — | FIXED AND VERIFIED (Stage 1) |
| AUD-10 | P2 | 4 | `backend/app/core/security.py`, `backend/app/api/v1/auth.py`, new refresh-session model + migration, `frontend/shared/api.js` | **021** (planned, Stage 4) | NOT STARTED |
| AUD-11 | P2 | 1 | `backend/app/core/throttle.py` (`client_ip`), `backend/app/core/config.py` (trusted-proxy setting) | — | FIXED AND VERIFIED (Stage 1) |
| AUD-12 | P2 | 1 | Upload handlers: `api/v1/users.py`, `api/v1/posts.py`, `api/v1/matches.py`, `api/v1/invites.py`; shared helper in `backend/app/core/storage.py` | — | FIXED BUT NOT FULLY VERIFIED (Stage 1 — helper-level tests pass; endpoint integration tests in Stage 3 suite) |
| AUD-13 | P2 | 2 | Migration 020 (canonical pair index), `backend/app/api/v1/invites.py` (send path) | **020** | NOT STARTED |
| AUD-14 | P2 | 7 | Proposal only (public card vs. authenticated) — no code change without approval | — | OWNER DECISION REQUIRED |
| AUD-15 | P3 | 1+2 | `backend/app/api/v1/invites.py` (accept), `backend/app/api/v1/players.py` (like), `posts.py` (like) | — | FIXED BUT NOT FULLY VERIFIED (Stage 1 portion — accept/like paths; concurrency proof in Stage 2/3) |
| AUD-16 | P3 | 1 | `backend/app/core/media.py` (decode/re-encode helpers), avatar/post/evidence handlers | — | FIXED BUT NOT FULLY VERIFIED (Stage 1 — normalize helper verified; endpoint integration in Stage 3 suite) |
| AUD-17 | P3 | 1 | `backend/app/schemas/user.py` (ProfileUpdate), `backend/app/api/v1/users.py` | — | FIXED AND VERIFIED (Stage 1) |
| AUD-18 | P3 | 1 | `backend/app/api/v1/auth.py` (login dummy verify) | — | FIXED AND VERIFIED (Stage 1) |
| AUD-19 | P3 | 4 | `backend/app/core/throttle.py` (policy), `backend/app/api/v1/auth.py` | — | NOT STARTED |
| AUD-20 | P3 | 2 | `backend/app/core/throttle.py` (atomic upsert), `backend/app/models/auth_throttle.py` | — | NOT STARTED |
| AUD-21 | P3 | 4 | New per-user write quotas (posts/tournaments/follows create paths), config in `core/config.py` | — | NOT STARTED |
| AUD-22 | P3 | 4 | `backend/app/main.py` (header middleware, dedupe vs. vercel.json), `vercel.json` untouched | — | NOT STARTED |
| AUD-23 | P3 | 4+7 | Ops checklist (this doc §5); `backend/app/api/v1/internal.py` guard already sound | — | NOT STARTED |
| AUD-24 | P3 | 4 | `backend/requirements.txt` + root `requirements.txt` (PyJWT), `backend/app/core/security.py`, password byte-length policy in `schemas/user.py`/`schemas/auth.py` | — | NOT STARTED |
| AUD-25 | P3 | 1 | `backend/app/api/v1/matches.py`, `backend/app/api/v1/invites.py` (submit paths), shared `MAX_SCORE` constant | — | FIXED BUT NOT FULLY VERIFIED (Stage 1 — cap wired in both submit paths; boundary API tests in Stage 3 suite) |
| AUD-26 | P3 | 7 | Documented policy (public match reads) — no change without approval | — | DEFERRED (documented) |
| AUD-27 | P3 | 6 | `frontend/web/app/ratings.html` (criteria subtitle), `frontend/web/app/arena-star.html`, docs note in this file §6 | — | NOT STARTED |
| AUD-28 | P3 | 5 | `backend/app/api/v1/fraud.py`, `frontend/web/app/admin.html` (signal visibility) — human review only, never auto-penalty | — | NOT STARTED |
| AUD-29 | P3 | 7 | Cleanup proposal only (dead tables + prize stubs inventory §6) | — (proposal) | DEFERRED (proposal in Stage 7) |
| AUD-30 | P3 | 0+7 | Documented in §1 of this file; branch actions are owner decisions | — | DOCUMENTED (Stage 0); decisions OWNER DECISION REQUIRED |
| AUD-31 | P3 | 6 | `backend/app/core/groups.py`, `backend/app/schemas/tournament.py`, `backend/app/models/*.py` (TYPE_CHECKING imports), `backend/app/api/v1/invites.py` (respond dedup) | — | NOT STARTED |
| AUD-32 | P3 | 1 | `frontend/shared/api.js` (export escapeHtml), 9 app pages + `admin.html` (remove copies), TDZ order in `ratings.html`/`profile.html` resolved by the shared helper | — | FIXED AND VERIFIED (Stage 1) |
| AUD-33 | P3 | 5 | `frontend/shared/i18n.js` (reverse map after all assigns; missing fr/en strings), coverage check script | — | NOT STARTED |
| AUD-34 | P3 | 1+5 | `frontend/shared/api.js` (refresh-fail → login), `frontend/shared/nav.js` (interval cleanup), `frontend/web/app/ratings.html` (loading/retry), `frontend/shared/i18n.js` (observer batching), attribute escaping in dashboard/match/tournament pages | — | IN PROGRESS (Stage 1 critical portions done: force-reauth + attribute escaping; remainder Stage 5) |
| AUD-35 | P3 | 7 | Assessment only (media volume, object-storage options) | — | DEFERRED (assessment in Stage 7) |

---

## 4. Stage 1 implementation plan (next stage — starts only from this baseline)

Scope (mission §3 Stage 1): AUD-09, AUD-11, AUD-12, AUD-15 (invite-accept + like paths), AUD-16, AUD-17, AUD-18, AUD-25, AUD-32, AUD-34 (critical portions: refresh-fail re-login, attribute escaping).

Order inside the stage (security impact first):
1. **AUD-09 + AUD-32 together** — shared `escapeHtml` exported from `shared/api.js`; invites.html error paths use it (kills AUD-09 at the root and removes the duplication class); delete per-page copies; verify every page still renders (node --check + grep: zero local definitions).
2. **AUD-17** — remove `avatar_url` from `ProfileUpdate` (schema) + confirm `update_own_profile` setattr loop no longer receives it; API test: PATCH with avatar_url → field ignored/absent in response.
3. **AUD-18** — dummy bcrypt verify on unknown-email login (constant-work path); keep generic 401.
4. **AUD-25** — `MAX_SCORE = 30` shared constant; validate in match submit, challenge submit **before** any state claim; boundary tests (0 ok, 30 ok, 31 → 400, negative → 400 as today).
5. **AUD-12 + AUD-16 together** — one streaming reader helper (`read_upload_limited`) in `core/storage.py` (count while reading, abort at cap+1) + one image normalization helper in `core/media.py` (Pillow decode → verify format → re-encode WebP for avatars/posts; evidence keeps its authorization model, bytes normalized the same way); apply to all four upload surfaces; oversized-multipart and non-image tests.
6. **AUD-15 (Stage 1 portion)** — catch `IntegrityError` on invite-accept and like commits → rollback → 409 (concurrency tests land in Stage 2/3 with PostgreSQL; Stage 1 verifies the code path with unit-level tests + code review).
7. **AUD-11** — `client_ip` trusts XFF only when the deployment declares a trusted proxy (new setting `TRUST_PROXY_HEADERS`, default: trust on Vercel via `VERCEL` env presence, distrust otherwise); tests for spoofed vs. trusted headers.
8. **AUD-34 critical portions** — `api.js`: failed refresh → clear tokens + redirect to login (no stranded sessions); escape enum/ID interpolations in dashboard/match/tournament templates via the shared helper.

Stage 1 test note: full PostgreSQL concurrency/integration tests are Stage 2–3 deliverables; Stage 1 ships unit tests (pure functions, schema validation, header logic) + syntax/compile/pyflakes gates + a local import smoke test, and records precisely which verifications are deferred to the PostgreSQL suite. No stage is marked complete on code alone.

---

## 5. Operations checklist — AUD-23 (prepared, Stage 4/7)

- [ ] After any production migration: unset `MIGRATION_SECRET` in the Vercel project; verify `GET /internal/migrate` → 503.
- [ ] Confirm `CRON_SECRET` remains set (maintenance sweep depends on it); verify `GET /internal/maintenance` without header → 401.
- [ ] Secrets exist only in the deployment environment — never in repo, logs, or this document.

## 6. Standing documentation (AUD-26, AUD-27, AUD-29 inventories)

- **AUD-26 — public match reads (current policy, retained):** `GET /matches/{id}` and `GET /tournaments/{id}/matches` are unauthenticated by design; exposed data is competition-public (fixtures, scores, winners). IDs are UUIDs. No change without owner approval.
- **AUD-27 — two rankings (current semantics, retained):** the public leaderboard orders by points → goal difference → goals → ELO → wins (`ratings.py`); Arena Star orders strictly by ELO (`players.py`); player titles are ELO thresholds. Stage 6 makes the criteria explicit in the UI; formulas are not merged without a product decision.
- **AUD-29 — dead economy inventory:** tables `transactions`, `wallets`, `withdrawal_requests` (migration 006; no models, no code references); stubs `_distribute_knockout_prize` (no-op) and `_refund_and_remove` (delete-only) in the API; `entry_fee`/`prize_pool` hardcoded 0 at tournament creation. Cleanup = separate owner-approved proposal (Stage 7). Nothing is dropped or reactivated by this mission.

---

*End of Stage 0 baseline. Next: Stage 1 (plan in §4), gated on an unambiguous source of truth — confirmed above.*

---

## 7. Stage 1 completion note (2026-11-03)

Implemented on `remediation/audit-2026-11-03`: AUD-09, AUD-11, AUD-12, AUD-15 (Stage-1 portion), AUD-16, AUD-17, AUD-18, AUD-25, AUD-32, AUD-34 (critical portions). New shared pieces: `core/competition.py` (MAX_SCORE=30), `core/media.py::read_upload_limited` (streamed cap, HTTP 413) + `normalize_image` (Pillow decode → WebP) + `evidence_media_type`; `frontend/shared/api.js` now owns the single `escapeHtml` global and `forceReauth()` on dead sessions. Oversize uploads now answer **413** (previously 400 after full buffering). Verification: compile OK, app import OK (85 routes), pyflakes back at the pre-existing baseline of 10 (AUD-31 scope), unit checks for every new helper PASS, JS syntax 10/10 edited pages PASS, XSS payload renders as text. PostgreSQL-level integration/concurrency verification for AUD-12/15/16/25 is scheduled in the Stage 2/3 suite (no local PostgreSQL exists on this workstation — see §1).
