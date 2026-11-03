# Proposal — AUD-30: Branch dispositions (26 branches)

Status: **PROPOSAL READY — no branch deleted or renamed.** Census
taken 2026-11-03 via the GitHub API (head SHA + last commit date).
Branch actions are owner decisions; the three `arena/*` branches are
the owner's AI working branches and are never touched.

## Keep — active lines

| Branch | Head | Last commit | Role |
|---|---|---|---|
| `deploy/vercel` | b7350af2e0 | 2026-11-02 | **Production.** The only deployment source for the live site. |
| `remediation/audit-2026-11-03` | 56c693c0a5 (+ Stage 7) | 2026-11-03 | This remediation. Disposition after review: merge into `deploy/vercel` (fast-forward is impossible — deploy by the established Git Data API flow), then delete. |
| `deploy/botkeep` | 6abf72aa31 | 2026-10-30 | Alternate deployment track (dependency host). Keep while that track exists. |
| `arena/01a0e0b2-…` | aa76463d86 | 2026-10-10 | Arena AI working branch — owner only. |
| `arena/01a05141-…` | 02c97f13cd | 2026-08-30 | Arena AI working branch — owner only. |
| `arena/01a08730-…` | b4aef0089b | 2026-09-26 | Arena AI working branch — owner only. |

## Archive-then-delete candidates — historical phase lines

All merged-into-history development phases from Aug–Sep 2026. Their
content lives on in the production line's history; the branches
themselves are stale pointers. Proposal: tag each `archive/<name>`
if the owner wants a permanent marker, then delete the branch.

| Branch | Head | Last commit |
|---|---|---|
| `phase2-competition-engine` | 392eaa8d3c | 2026-08-30 |
| `phase3-verification-engine` | 8ab5b6722f | 2026-08-31 |
| `phase4-trust-fraud-engine` | f4c50426c6 | 2026-08-31 |
| `phase5-community-engine` | 20d3fa7fc3 | 2026-08-31 |
| `phase7-economy-engine` | 49907f8276 | 2026-08-31 |
| `phase8-analytics` | 5fea444e61 | 2026-09-01 |
| `phase8-seasons` | 3e8ba38587 | 2026-09-01 |
| `phase8a-league-engine` | 511f9d388a | 2026-09-01 |
| `phase8b-draw-system` | 5bd9454cfb | 2026-09-01 |
| `phase8d-participant-approval` | cf955e660e | 2026-09-01 |
| `phase8e-fix-cyclic-tiebreak` | 4d04264007 | 2026-09-02 |
| `phase8e-fix-head-to-head` | 44c0984272 | 2026-09-02 |
| `phase8e-group-knockout` | 194605ee43 | 2026-09-01 |
| `critical-fixes-round1` | 2e74c6ebe2 | 2026-09-05 |
| `high-priority-fixes-round2` | b0403d44d4 | 2026-09-05 |
| `feat/visual-identity` | 9e6df1eb8b | 2026-09-07 |
| `feat/ui-phase-1` | e538404d75 | 2026-09-07 |
| `push-compose` | 95ea2a553b | 2026-09-07 |
| `anwarefahmi22-repo-analysis` | 25f0b24688 | 2026-09-09 |

## Special case — `main`

`main` (2d89573f13, 2026-09-27) is the GitHub **default branch** but
is a stale PR line and **not** a deployment source. Two-step
proposal: (1) change the repository default branch to
`deploy/vercel` in GitHub settings (owner action), so clones and PRs
target the real line; (2) then archive/delete `main` like the phase
lines. Until step 1 happens, keep `main` — deleting the default
branch is blocked by GitHub anyway.

## Explicitly out of scope

No branch in this document was deleted, renamed, or retargeted by
the remediation. The `arena/*` branches are listed for completeness
only.
