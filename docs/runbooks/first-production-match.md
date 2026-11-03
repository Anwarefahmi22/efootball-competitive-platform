# Runbook — First Supervised Production Match (AUD-02)

Status: **READY — execution requires the owner's explicit scheduling and
production approval.** Nothing in this runbook has been run against
production. Production `player_ratings` is empty today: no real match
has ever completed, so the platform's core promise (a verified result
moving a real rating) is unproven on live data even though the full
lifecycle is test-proven on the remediation branch (Stage 3/5 suites).

## Why a challenge match, not a tournament

A 1-v-1 challenge exercises the same submit → confirm → ELO path with
two accounts and no bracket, draw, or third parties. A tournament
final additionally exercises bracket advancement; do that second.

## Participants

Two real, consenting accounts. Known candidates (owner's choice):
the owner's two accounts (#1001 admin, #1004) or #1004 vs the first
external player (#1010 «Swisher abdou»). QA/probe accounts must never
be used as "real" match participants.

## Preconditions (verify before starting)

1. Production is on the intended build; `GET /health` returns 200.
2. Both accounts can log in; both have profiles.
3. Record the starting state through the API (not the DB console):
   `GET /ratings/leaderboard` (expect: does not contain either player),
   `GET /players/cards` for both arena numbers, `GET /trust/{id}` = 100.
4. Agree the real fixture and the honest final score in advance; the
   evidence photo must be a genuine screenshot of that score.

## Sequence

1. Player A sends a match invite (Arena Star → Invite Match, or
   `POST /invites/match`).
2. Player B accepts within 72h (`POST /invites/match/{id}/accept`) → a
   challenge in READY state exists.
3. Play the match for real.
4. The designated submitter submits the true score **with the evidence
   screenshot** (`POST /challenges/{id}/submit-result`).
5. The opponent confirms (`POST /challenges/{id}/confirm`) — only if
   the score is accurate. If it is not, dispute instead and stop: that
   becomes a dispute-path exercise, which is also valuable, but say so
   in the log.

## Invariants to verify immediately after confirmation

- Challenge status = `completed`; `winner_id` correct.
- Exactly one rating row per player appears on
  `GET /ratings/leaderboard` with the mathematically expected values
  (equal 1000 starters: winner **1016**, loser **984** for a decisive
  result; a draw leaves both at 1000 with draws=1).
- Re-confirming is impossible (second confirm → 400) — do **not** test
  this against the real challenge if it would disturb the record;
  it is already test-proven. Simply note the completed state.
- `GET /trust/{id}` still 100 for both (a clean confirmed match does
  not reduce trust), and the match shows in both players' challenge
  lists and on their Arena Star cards (matches_played = 1).

## Abort / rollback posture

There is no undo for a confirmed ELO application by design (the audit
verified exactly-once semantics). If anything looks wrong, STOP,
record the responses, and escalate to a reviewed data correction —
never hand-edit ratings without a written decision. A wrong-score
submission before confirmation is safe: the opponent disputes, an
admin resolves with the true score.

## After-action

Log date, accounts, challenge id, submitted/confirmed scores, observed
ELO values, and any surprise in `REMEDIATION_TRACKING.md` (AUD-02) and
close the finding as FIXED AND VERIFIED.
