# Decision — AUD-14: Should player cards be public?

Status: **OWNER DECISION REQUIRED.** No code changed. The mission
forbids changing the access policy without explicit owner approval.

## Current state

`GET /players/cards` and the Arena Star page require a logged-in
account. Any registered user can already see every card: display
name, country, eFootball IGN, verified badge, ELO, match record,
tournament cups, formation, collective strength, the uploaded squad
screenshot, like count, and arena number.

## Option A — Public read-only cards

Anonymous `GET /players/cards/{arena_no}` (single card, not the full
list) plus a public card page whose link can be shared outside the
platform.

- **For:** sharing is the growth loop — a player sending their card to
  friends is the cheapest distribution the platform has; cards are
  designed as identity objects; everything on a card is information
  the player chose to publish in-app.
- **Against:** anonymous scraping/enumeration of the whole player
  base becomes trivial (mitigated by single-card-only access +
  pagination + rate limits, never eliminated); squad screenshots and
  IGNs become indexable; players who joined expecting a members-only
  space get a policy change they did not consent to — a notice +
  opt-out (hide my card publicly) would be the responsible rollout.
- **Cost:** small — an unauthenticated single-card endpoint, a public
  page variant, the opt-out profile flag, tests.

## Option B — Keep cards authenticated (status quo)

- **For:** zero new exposure; the in-app discovery loop already
  works; no consent questions.
- **Against:** every shared card link lands on a login wall, which
  kills the viral loop the card design was built for.

## Recommendation

Option A **with the opt-out flag and single-card-only access**, when
the owner decides distribution matters more than the marginal
exposure — which is a product-timing call, not an engineering one.
Until then, B remains in force by default.

## If A is approved, the follow-up work is

1. `GET /players/public/{arena_no}` (no auth; 404 for opted-out or
   inactive players).
2. `profiles.public_card` boolean (default true, migration) + a
   profile-settings toggle.
3. Public card page reusing the Arena Star card markup, no actions.
4. Rate-limit the endpoint via the existing throttle counters.
