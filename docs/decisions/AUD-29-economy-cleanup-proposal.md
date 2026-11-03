# Proposal — AUD-29: Retire the unused economy scaffolding

Status: **PROPOSAL READY — nothing dropped, nothing changed.** The
mission forbids dropping tables without explicit owner approval.

## Inventory of what exists but is never used

Database (created by migration `006_economy_engine`):
- `wallets` (user_id FK → users, balance)
- `transactions`
- `withdrawal_requests`

Code:
- **No ORM models** exist for these tables (`backend/app/models/` has
  no economy module), no API route reads or writes them, no frontend
  surface references wallets or withdrawals. They are schema-only
  residue from the Phase 7 economy engine that was built as tables
  and never wired to a product flow.
- Tournament prize stubs: `tournaments.entry_fee`,
  `tournaments.prize_pool`, `tournaments.prize_distributed` columns
  exist; tournament **creation forces entry_fee=0 / prize_pool=0**
  (`tournaments.py`), no code charges a fee or distributes a prize,
  and no UI displays either field.

## Evidence of non-use

- Zero references to the three tables anywhere in `backend/app` or
  `frontend` (grep-verified at audit time and re-verified in Stage 7).
- Production data: the tables were created empty by migration 006 and
  no writer exists, so they hold no user value. (Confirm row counts
  are 0 as step 1 of any execution — via the API-independent DB check
  the owner runs, per the mission's production-data rules.)

## Proposed execution (only on owner approval)

1. Verify `wallets` / `transactions` / `withdrawal_requests` row
   counts are 0 on production; take a database backup/snapshot.
2. New migration (next number after the then-current head) dropping
   the three tables; downgrade recreates them empty (schema-only
   restore — there is no data to restore).
3. Keep the tournament columns for one release (they are referenced
   by the ORM model and schemas), then decide separately whether to
   drop `entry_fee` / `prize_pool` / `prize_distributed` or keep them
   as the seed of a future real prize feature.
4. Run the full test suite + a production smoke check after deploy.

## Risks

- A hidden consumer (an old branch, an external script) writing to
  these tables would break — mitigated by the grep evidence and by
  doing step 1–2 in one maintenance window with the backup in hand.
- If a real economy feature is planned soon, dropping and recreating
  costs one migration either way; the cleanup is cheap to reverse at
  schema level.

## Recommendation

Approve the drop of the three tables (step 2) at the next planned
production migration window — ideally bundled with migration 020/021
deployment so production takes one schema event, not three. Keep the
tournament columns decision separate.
