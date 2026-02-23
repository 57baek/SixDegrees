# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-22)

**Core value:** The People Map — every user is always at (0,0), all others positioned by profile similarity + interaction intensity, updated daily
**Current focus:** Phase 2 — Algorithm Pipeline

## Current Position

Phase: 2 of 5 (Algorithm Pipeline) — IN PROGRESS
Current Plan: 02-03 complete
Next: Phase 2 Plan 04 — t-SNE Projector and Full Pipeline (02-04)
Status: Plan 02-03 complete — combined distance matrix and origin translator built and tested (17 TDD tests green)
Last activity: 2026-02-23 — Plan 02-03 complete; build_combined_distance_matrix() and translate_and_assign_tiers() implemented

Progress: [██████░░░░] 38%

## Performance Metrics

**Velocity:**
- Total plans completed: 5
- Average duration: ~12min (01-01: ~45min including checkpoint, 01-02: ~4min, 02-01: ~2min, 02-02: ~6min, 02-03: ~2min)
- Total execution time: ~1.0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-database-foundation | 2 complete / 2 total | ~49min | ~24min |
| 02-core-algorithm | 3 complete / 4 total | ~10min | ~3min |

**Recent Trend:**
- Last 5 plans: 01-02 (~4min), 02-01 (~2min), 02-02 (~6min), 02-03 (~2min)
- Trend: Fast execution for pure coding tasks

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- t-SNE over PCA: `metric='precomputed'` requires `init='random'` — NOT 'pca' (crashes)
- α=0.6, β=0.4 defaults in `backend/config/algorithm.py` — no magic numbers in algorithm code
- Dict-driven INTERACTION_WEIGHTS: adding new type = 1 column + 1 dict entry, zero logic changes
- Canonical pair ordering in interactions table (user_id_a < user_id_b) — prevents duplicate rows
- Batch precompute + store: t-SNE is expensive; precompute at 7pm, serve from DB
- No FK from user_profiles.user_id to auth.users — seed users won't exist in auth.users, FK would block inserts
- FK constraints on interactions wrapped in DO $$ block for idempotency (plan 01-01)
- RLS enabled on all 3 tables; service role key used in all backend DB access (plan 01-01)
- Column names in user_profiles are location_city/location_state (not city/state) — matches DDL from plan 01-01
- Hardcoded UUIDs in seed script for idempotent upserts — same PKs on every re-run
- max_iter=1000 (not n_iter) — parameter renamed in sklearn 1.5; old name causes DeprecationWarning in 1.8.0 (plan 02-01)
- perplexity = min(30, max(5, int(sqrt(N)))) — at N=10 gives perplexity=5, safely < N (plan 02-01)
- scikit-learn 1.8.0, numpy 2.4.2 installed in backend venv (plan 02-01)
- np.percentile(method='lower') for 95th-pct clip: picks actual observed data point as cap, avoids interpolated threshold near outlier (plan 02-02)
- Normalize by clip_val not clipped.max(): anchors at 0 so missing pairs always score 0.0 without special-case code (plan 02-02)
- Field name mapping (city/state vs location_city/location_state) deferred to Phase 3 data_fetcher.py — UserProfile unchanged to avoid breaking /match routes (plan 02-03)
- Tier assignment uses 2D Euclidean distance from translated coordinates, not get_ranked_matches() — avoids 0.75 cutoff that would drop outer users (plan 02-03)

### Pending Todos

None.

### Blockers/Concerns

- Known bug: `handleLogout()` in `Home.vue` scoped inside `loadPosts()` — crashes on logout. Out of scope this milestone but worth noting.
- APScheduler single-worker constraint: multi-worker uvicorn causes double-firing. Must document clearly.
- Supabase RLS: verify service role key is used for all backend DB reads (not anon key). Verified for algorithm tables; existing match routes not yet validated.
- `psycopg2-binary` fails to build on macOS arm64 + Python 3.14. Not blocking for seed script (supabase-py uses HTTP). May need resolution before SQLAlchemy usage in later phases.

## Session Continuity

Last session: 2026-02-23
Stopped at: Plan 02-03 complete. Next: Phase 2 Plan 04 — t-SNE Projector and Full Pipeline (02-04).
