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
| AUD-01 | P1 | 3 | `backend/tests/` (new), `.github/workflows/ci.yml` (new), `backend/app/**` (subjects) | — | FIXED AND VERIFIED (Stage 3 — 34-test suite green locally and from a clean venv; CI workflow added; branch-protection required-check remains an owner-side GitHub setting) |
| AUD-02 | P1 | 7 | Runbook in final decisions pack (operations only) | — | DOCUMENTED (Stage 7 — supervised first-match runbook at docs/runbooks/first-production-match.md; execution awaits owner scheduling + production approval; production player_ratings still empty) |
| AUD-03 | P2 | 6 | `backend/app/api/v1/players.py`, `backend/app/schemas/player.py`, `frontend/web/app/arena-star.html` | — | FIXED AND VERIFIED (Stage 6 — GET /players/cards accepts limit (default 50, max 100) + offset over the unchanged rating/arena_no order; pagination tiling test proves pages reassemble the full list exactly once; Arena Star deck loads 24/page with load-more appending to the fan's back and ?player= deep links paging until found; admin panel requests limit=100) |
| AUD-04 | P2 | 2 | `backend/alembic/versions/020_*.py` (new) | **020** | FIXED AND VERIFIED (Stage 2 — migration 020 upgrade/downgrade/upgrade on PostgreSQL 16; 19 indexes present) |
| AUD-05 | P2 | 6 | `backend/app/api/v1/invites.py` (`_brief`, inbox, challenge reads) | — | FIXED AND VERIFIED (Stage 6 — _briefs batch-loads users+profiles in 2 queries; challenge reads batch latest evidence in 1; query-count regression tests: inbox of 6 invites ≤12 queries total (was ~25+), challenge list ≤8) |
| AUD-06 | P2 | 2 | `backend/app/api/v1/tournaments.py` (join), `backend/app/api/v1/invites.py` (tournament accept) | — | FIXED AND VERIFIED (Stage 2 — row locks + concurrent PostgreSQL tests pass) |
| AUD-07 | P2 | 5 | `backend/app/api/v1/admin.py`, `backend/app/schemas/admin.py` (verify schemas), `frontend/web/app/admin.html` | — (is_verified column exists) | FIXED AND VERIFIED (Stage 5 — POST/DELETE /admin/users/{id}/verify, admin-gated, idempotent, 404 unknown; admin page gained a verification panel over the player cards; badge state proven on the Arena Star card payload) |
| AUD-08 | P2 | 5 | `backend/app/api/v1/posts.py`, `frontend/web/app/community.html` | — (cascades exist) | FIXED AND VERIFIED (Stage 5 — DELETE /posts/{id} and /posts/{id}/comments/{cid}: author or admin, others 403, cascades + stored-image cleanup; community UI shows delete only to author/admin via the new /auth/me is_admin flag, render logic unit-tested) |
| AUD-09 | P2 | 1 | `frontend/web/app/invites.html` (error render paths ~L157, L184–191) | — | FIXED AND VERIFIED (Stage 1) |
| AUD-10 | P2 | 4 | `backend/app/core/security.py`, `backend/app/api/v1/auth.py`, new refresh-session model + migration, `frontend/shared/api.js` | **021** (planned, Stage 4) | FIXED AND VERIFIED (Stage 4 — migration 021 refresh_sessions; rotation, token families, reuse detection with 30s tab-race grace, hash-only storage, /auth/logout revocation; old jti-less refresh tokens rejected = documented one-time re-login at deploy) |
| AUD-11 | P2 | 1 | `backend/app/core/throttle.py` (`client_ip`), `backend/app/core/config.py` (trusted-proxy setting) | — | FIXED AND VERIFIED (Stage 1) |
| AUD-12 | P2 | 1 | Upload handlers: `api/v1/users.py`, `api/v1/posts.py`, `api/v1/matches.py`, `api/v1/invites.py`; shared helper in `backend/app/core/storage.py` | — | FIXED AND VERIFIED (Stages 1+3 — endpoint tests: 413 oversize, streamed abort) |
| AUD-13 | P2 | 2 | Migration 020 (canonical pair index), `backend/app/api/v1/invites.py` (send path) | **020** | FIXED AND VERIFIED (Stage 2 — canonical pair index in 020 + 409 translation; concurrent test passes) |
| AUD-14 | P2 | 7 | Proposal only (public card vs. authenticated) — no code change without approval | — | OWNER DECISION REQUIRED (Stage 7 — options + recommendation at docs/decisions/AUD-14-public-player-cards.md; authenticated policy unchanged) |
| AUD-15 | P3 | 1+2 | `backend/app/api/v1/invites.py` (accept), `backend/app/api/v1/players.py` (like), `posts.py` (like) | — | FIXED AND VERIFIED (Stages 1–2 — double-accept concurrency test passes) |
| AUD-16 | P3 | 1 | `backend/app/core/media.py` (decode/re-encode helpers), avatar/post/evidence handlers | — | FIXED AND VERIFIED (Stages 1+3 — endpoint tests: non-image 400, WebP normalization on avatar + evidence) |
| AUD-17 | P3 | 1 | `backend/app/schemas/user.py` (ProfileUpdate), `backend/app/api/v1/users.py` | — | FIXED AND VERIFIED (Stage 1) |
| AUD-18 | P3 | 1 | `backend/app/api/v1/auth.py` (login dummy verify) | — | FIXED AND VERIFIED (Stage 1) |
| AUD-19 | P3 | 4 | `backend/app/core/throttle.py` (policy), `backend/app/api/v1/auth.py` | — | FIXED AND VERIFIED (Stage 4 — lock keyed to (email, IP) pair + per-IP lock; victim-at-another-IP test passes; distributed-guessing trade-off documented in throttle.py) |
| AUD-20 | P3 | 2 | `backend/app/core/throttle.py` (atomic upsert), `backend/app/models/auth_throttle.py` | — | FIXED AND VERIFIED (Stage 2 — atomic upsert; 30-way concurrent count test passes) |
| AUD-21 | P3 | 4 | New per-user write quotas (posts/tournaments/follows create paths), config in `core/config.py` | — | FIXED AND VERIFIED (Stage 4 — enforce_quota on post 20/h, comment 60/h, tournament 10/h, follow 120/h; match/challenge operations deliberately unquota'd; 429 + per-user isolation tests) |
| AUD-22 | P3 | 4 | `backend/app/main.py` (header middleware, dedupe vs. vercel.json), `vercel.json` untouched | — | FIXED AND VERIFIED (Stage 4 — in-app middleware mirrors vercel.json + HSTS, set-only-if-absent so the Vercel track never duplicates) |
| AUD-23 | P3 | 4+7 | Ops checklist (this doc §5); `backend/app/api/v1/internal.py` guard already sound | — | OWNER DECISION REQUIRED (Stage 7 — decision doc at docs/decisions/AUD-23-migration-secret.md recommends leaving MIGRATION_SECRET unset while deploys are manual; endpoint verified fail-closed 503) |
| AUD-24 | P3 | 4 | `backend/requirements.txt` + root `requirements.txt` (PyJWT), `backend/app/core/security.py`, password byte-length policy in `schemas/user.py`/`schemas/auth.py` | — | FIXED AND VERIFIED (Stage 4 — PyJWT 2.10.1 replaces python-jose in BOTH requirements files, wire format unchanged; password policy enforces bcrypt's 72-BYTE limit, rejecting multibyte overflows that were silently truncated) |
| AUD-25 | P3 | 1 | `backend/app/api/v1/matches.py`, `backend/app/api/v1/invites.py` (submit paths), shared `MAX_SCORE` constant | — | FIXED AND VERIFIED (Stages 1+3 — boundary tests in both submit paths) |
| AUD-26 | P3 | 7 | Documented policy (public match reads) — no change without approval | — | DOCUMENTED (Stage 7 — risk assessment + retain recommendation at docs/decisions/AUD-26-public-match-reads.md; owner sign-off pending; no code changed) |
| AUD-27 | P3 | 6 | `frontend/web/app/ratings.html` (criteria subtitle), `frontend/web/app/arena-star.html`, docs note in this file §6 | — | FIXED AND VERIFIED (Stage 6 — leaderboard SQL gained a deterministic final tiebreak; the ratings page now states the exact criteria matching the SQL: points, goal difference, goals for, ELO, wins; league standings criteria were already code-documented (points/GD/GF + deterministic key) in core/league.py) |
| AUD-28 | P3 | 5 | `backend/app/api/v1/fraud.py`, `frontend/web/app/admin.html` (signal visibility) — human review only, never auto-penalty | — | FIXED AND VERIFIED (Stage 5 — collusion endpoint now scans BOTH tournament and challenge matches with win splits, surfaced in a new admin-page signals panel; strictly read-only, trust/ELO untouched by reads — asserted in tests) |
| AUD-29 | P3 | 7 | Cleanup proposal only (dead tables + prize stubs inventory §6) | — (proposal) | PROPOSAL READY (Stage 7 — docs/decisions/AUD-29-economy-cleanup-proposal.md: wallets/transactions/withdrawal_requests are schema-only residue with zero code references, verified by grep; tournament prize columns kept as a separate decision; NOTHING dropped) |
| AUD-30 | P3 | 0+7 | Documented in §1 of this file; branch actions are owner decisions | — | PROPOSAL READY (Stage 7 — docs/decisions/AUD-30-branch-dispositions.md: fresh 26-branch census with heads/dates; keep deploy/*, remediation, arena/* (never touched); archive-then-delete proposed for 19 historical lines; main default-branch switch is an owner action; NO branch deleted) |
| AUD-31 | P3 | 6 | `backend/app/core/groups.py`, `backend/app/schemas/tournament.py`, `backend/app/models/*.py` (TYPE_CHECKING imports), `backend/app/api/v1/invites.py` (respond dedup) | — | FIXED AND VERIFIED (Stage 6 — pyflakes 11 -> 0: unused imports removed, string-only model references resolved with TYPE_CHECKING imports, models/__init__ re-exports declared in __all__; invites: 6 response handlers share _load_actionable_invite with identical messages/codes, read builders factored into pure *_from constructors) |
| AUD-32 | P3 | 1 | `frontend/shared/api.js` (export escapeHtml), 9 app pages + `admin.html` (remove copies), TDZ order in `ratings.html`/`profile.html` resolved by the shared helper | — | FIXED AND VERIFIED (Stage 1) |
| AUD-33 | P3 | 5 | `frontend/shared/i18n.js` (reverse map after all assigns; missing fr/en strings), coverage check script | — | FIXED AND VERIFIED (Stage 5 — root cause fixed: reverse map rebuilds whenever the dictionary grows, so the 9+ dictionary blocks appended after its construction now round-trip fr<->en/ar, proven in Node; dictionary audit: 794 entries, 0 missing fr/en; 25 new Stage 5 strings added with both translations; 11 duplicate keys carry equivalent wording variants, deterministic last-wins) |
| AUD-34 | P3 | 1+5 | `frontend/shared/api.js` (refresh-fail → login), `frontend/shared/nav.js` (interval cleanup), `frontend/web/app/ratings.html` (loading/retry), `frontend/shared/i18n.js` (observer batching), attribute escaping in dashboard/match/tournament pages | — | FIXED AND VERIFIED (Stages 1+5 — Stage 1: forceReauth + attribute escaping; Stage 5: ratings page gained loading state + retry, nav invite-badge interval is cleared on pagehide, i18n MutationObserver coalesces DOM bursts into one rAF apply) |
| AUD-35 | P3 | 7 | Assessment only (media volume, object-storage options) | — | DOCUMENTED (Stage 7 — assessment at docs/decisions/AUD-35-object-storage-assessment.md: stay on Postgres media store until a named trigger (~2GB media / tier pressure / serving cost); media.py abstraction makes the later move a backend swap; evidence privacy rule recorded) |

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

---

## 8. Stage 2 completion note (2026-11-03)

Implemented: AUD-06 (tournament row lock in join + tournament-invite accept, reusing the existing `for_update` loader pattern), AUD-13 (migration 020 rebuilds `uq_match_invite_pending_pair` on LEAST/GREATEST; send-path IntegrityError → 409), AUD-20 (`record_hit` is now one atomic INSERT … ON CONFLICT DO UPDATE — identical window/lock semantics), AUD-04 (migration **020_fk_indexes_pair_invite**, parent 019: 19 new FK indexes; columns already leading an existing unique index were not duplicated). Test infrastructure: a self-contained **PostgreSQL 16.15** was installed via conda-forge (micromamba) at `/opt/pg-test/pg16`, running as user `pgtest` on 127.0.0.1:55432 with a disposable `arena_test` database — no production infrastructure was touched. The full migration chain 001→019 was first proven on real PostgreSQL, then 020 upgrade → downgrade → upgrade. New tests in `backend/tests/` (seed of the Stage 3 suite): **6/6 pass** — throttle atomicity (30 concurrent hits counted exactly), lock/window semantics, join capacity race, invite-accept capacity race, opposite-direction invite race, double-accept exactly-one-challenge.

---

## 9. Stage 3 completion note (2026-11-03)

AUD-01 delivered. Suite layout (`backend/tests/`, 34 tests): `test_elo.py` (pure ELO incl. zero-sum), `test_auth_api.py` (register/login/refresh, AUD-17/18 regressions), `test_uploads.py` (AUD-12/16 endpoint proof), `test_lifecycles.py` (match confirm exactly-once ELO, dispute → admin resolve, challenge flow + anti-farming, AUD-25 boundaries, approval/cancel), `test_authorization.py` (anonymous/non-admin/outsider matrix), `test_stage2_concurrency.py` (Stage 2 races), `test_migrations.py` (dedicated scratch DB: full chain up/down/up). Fixtures refuse non-test DSNs. Config: `backend/pytest.ini`, `backend/requirements-dev.txt` (pinned). CI: `.github/workflows/tests.yml` (PostgreSQL 16 service, migrations, pytest). Clean-environment proof: fresh venv installed from the two requirements files and ran **34/34 green**. Two test-authoring lessons recorded: EmailStr rejects reserved TLDs (fixtures use arena.dev), and the random bracket draw means tests must derive actors from the drawn match, never assume pairings (this caused one flaky failure, root-caused and fixed). Remaining owner-side step: mark the CI `pytest` job a required status check in GitHub branch protection for the remediation/production branches.

---

## 10. Stage 4 completion note (2026-11-03)

Delivered AUD-24 → AUD-10 → AUD-19 → AUD-21 → AUD-22, in that order (the JWT swap first so rotation builds on the maintained library). Migration **021_refresh_sessions** (upgrade/downgrade/upgrade verified on real PostgreSQL). Test suite is now **44 tests, all passing** (10 new in `tests/test_stage4_auth.py`). Design points worth remembering: refresh tokens are tracked by jti with SHA-256 hashes only; rotation keeps one family per login; replaying a retired token older than the 30-second grace window revokes the family, while a replay inside the window is rejected without revocation (racing browser tabs); logout revokes the presented token's family and is idempotent. AUD-19's pair-scoped lock knowingly trades a global per-email lock for immunity to targeted victim lockout — a distributed attacker now gets 5 guesses per IP, bounded by the 20-per-IP lock; that trade-off is written into `core/throttle.py` for the next reviewer. Pyflakes stands at 11: the Stage 4 delta is the `RefreshSession` registration import in `models/__init__.py`, same intentional pattern as the invite models, all cleared together by AUD-31 in Stage 6.

---

## 11. Stage 5 completion note (2026-11-03)

Suite now **47 tests, all passing** (3 new in `tests/test_stage5_community.py`). Two scope refinements worth recording: (1) AUD-28's backend signal endpoint already existed for tournament matches — the real gaps were that it ignored challenge matches (the farming surface) and that no UI ever called it; both are now closed. (2) AUD-07's `is_verified` lives on the `users` table (the Arena Star cards already read it from there) — the first implementation draft wrote it to the profile before the model check caught that; the shipped code writes the user column. `/auth/me` additionally returns `is_admin` (computed from the DB column) so clients can render admin affordances; authorization remains exclusively server-side. The admin page itself remains Arabic-first by its original design — its strings translate through the shared dictionary like every other page.

---

## 12. Stage 6 completion note (2026-11-03)

Suite now **50 tests, all passing** (3 new in `tests/test_stage6_perf.py`), and **pyflakes reports zero findings** across the backend (baseline was 10 at audit time). Notes: cards pagination slices the same Python-sorted list the endpoint always produced, so ordering semantics are unchanged — the endpoint still assembles all cards internally before slicing, which is proportionate at the platform's current scale and is the honest bound today; pushing the sort into SQL is the follow-up if the player count ever makes it matter. The invite inbox endpoint also had a second, older response construction that the batch refactor initially missed — caught by grepping for remaining per-item awaits, not by tests, which is why the query-count regression tests now exist.

---

## 13. Mission closure (2026-11-03)

All seven stages are complete. Final state of the audit's 35 findings:

- **FIXED AND VERIFIED — 26:** AUD-01, 03, 04, 05, 06, 07, 08, 09, 10, 11, 12, 13, 15, 16, 17, 18, 19, 20, 21, 22, 24, 25, 27, 28, 31, 33, 34.
- **DOCUMENTED / PROPOSAL READY — 5:** AUD-02 (runbook), AUD-26 (retain public reads), AUD-29 (economy cleanup), AUD-30 (branch dispositions), AUD-35 (storage assessment).
- **OWNER DECISION REQUIRED — 3:** AUD-14 (public cards), AUD-23 (MIGRATION_SECRET), plus the owner-side halves of AUD-29/AUD-30 executions and the AUD-01 branch-protection toggle.
- **PARTIALLY FIXED — 1:** AUD-23's preparation half (its final decision is the owner item above).
- AUD-32 is counted inside the FIXED set via Stage 1 (shared escapeHtml) — the table row carries its own status text.

Verification totals: **50 automated tests, all passing** on real PostgreSQL (suite also reproduced 34/34 from a clean venv at Stage 3 and re-run in full at every stage); **pyflakes: 0 findings**; migrations 020 + 021 each proven upgrade → downgrade → upgrade on real PostgreSQL. Production was never touched: no deploy, no production migration, no production data change. The remediation branch (`remediation/audit-2026-11-03`, 8 commits: Stages 0–7) is ready for the owner's review and merge decision.

### What the owner still decides (single list)

1. Merge `remediation/audit-2026-11-03` into `deploy/vercel` and deploy (includes applying migrations 020 + 021 to production and the documented one-time refresh re-login from AUD-10).
2. AUD-02: schedule the supervised first real production match (runbook ready).
3. AUD-14: public player cards — Option A (with opt-out) or keep authenticated.
4. AUD-23: leave MIGRATION_SECRET unset (recommended) or set it.
5. AUD-29: approve dropping the three dead economy tables (bundle with the 020/021 window).
6. AUD-30: approve branch archiving/deletions + default-branch switch.
7. GitHub: mark the CI `pytest` job a required status check.
8. Purge QA probe accounts 1011/1012/1013 on production (pending since before this mission — cascades the QA tournament + the diagnostic challenge on account #1004).
