# Decision — AUD-26: Public match reads

Status: **DOCUMENTED — recommendation: RETAIN.** Owner sign-off
pending; no code changed by the remediation.

## What is public today

Without any account, anyone can read:
- `GET /tournaments`, `GET /tournaments/{id}`, participant lists with
  display names, and tournament match lists (pairings, scores,
  statuses, winner).
- `GET /tournaments/{id}/matches` and individual match reads.
- `GET /ratings/leaderboard` (display names + full rating lines).
- `GET /posts` community feed reads.

## What is NOT public

Evidence images and evidence lists (participants/organizer/admins
only — verified in the audit and by the Stage 3 authorization tests),
profiles' private fields, emails (never exposed by any read model),
invites, challenges lists, trust history.

## Risk assessment

The exposed data is **competition data**: names players chose as
public display names, scores of matches played on a competitive
platform, tournament structures, and rankings. This is the same
category of information every sports platform publishes (fixtures and
results are the product's public face), and the landing page itself
links into tournaments and ratings for anonymous visitors — public
reads are load-bearing for the product's discovery experience, not
an oversight.

Residual risks are modest: bulk scraping of results (no personal
data beyond display names), and pre-match pairing visibility (by
design — players must know their opponents).

## Recommendation

Retain public reads for tournaments, matches, participants, and the
leaderboard. Keep the existing boundary exactly where it is:
evidence, invites, challenges, and account data stay authenticated.
Revisit only if a future feature adds genuinely private match data
(private notes, contact details) — at that point those fields, not
the whole surface, get access control.
