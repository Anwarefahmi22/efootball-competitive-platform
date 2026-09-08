# Architecture (Phase 1 context)

The platform is five systems around **Player Identity**:

1. **Competition** — tournaments, matches, rankings (later phases).
2. **Community** — social graph, posts, clubs (later phases).
3. **Live** — streams, match-day presence (later phases).
4. **Verification** — proving identity and in-game accounts (later phases).
5. **Competition integrity** — trust, evidence, disputes, and free tournaments. The platform does not process deposits, withdrawals, entry fees, or cash prizes.

Phase 1 only implements **Player Identity**: User + Profile models, registration/login/JWT, and public/own profile APIs. Other systems stay out of this codebase until their phases.
