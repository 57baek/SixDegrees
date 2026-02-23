# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-22)

**Core value:** The People Map — every user is always at (0,0), all others positioned by profile similarity + interaction intensity, updated daily
**Current focus:** Phase 4 — API and Scheduler

## Current Position

Phase: 4 of 5 (API and Scheduler) — IN PROGRESS
Current Plan: 04-01 complete
Next: Phase 4 Plan 02 — interaction endpoints (POST /interactions/like, /comment, /dm)
Status: Plan 04-01 complete — get_current_user JWT dependency and increment_interaction Postgres RPC both live
Last activity: 2026-02-23 — Plan 04-01 complete; shared auth foundation ready for all write endpoints

Progress: [██████████░] 65%

## Performance Metrics

**Velocity:**
- Total plans completed: 8
- Average duration: ~8min (01-01: ~45min including checkpoint, 01-02: ~4min, 02-01: ~2min, 02-02: ~6min, 02-03: ~2min, 02-04: ~2min, 03-01: ~2min, 03-02: ~1min)
- Total execution time: ~1.2 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-database-foundation | 2 complete / 2 total | ~49min | ~24min |
| 02-core-algorithm | 4 complete / 4 total | ~12min | ~3min |
| 03-pipeline-integration | 2 complete / 2 total | ~3min | ~1.5min |
| 04-api-and-scheduler | 1 complete / 4 total | ~13min | ~13min |

**Recent Trend:**
- Last 5 plans: 02-04 (~2min), 03-01 (~2min), 03-02 (~1min), 04-01 (~13min)
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
- pipeline.py is pure computation — no Supabase IO; Phase 3 wraps with data_fetcher/coord_writer (plan 02-04)
- raw_coords preserved in run_pipeline() output for future Procrustes alignment — not discarded after translation (plan 02-04)
- Smoke test for coord_writer used nil-UUID not string "test-center-000" — map_coordinates.center_user_id is UUID type, string literals fail DB validation (plan 03-01)
- occupation hardcoded to "" at DB boundary — user_profiles has no occupation column; UserProfile model requires it; boundary absorbs the mismatch (plan 03-01)
- No try/except in run_pipeline_for_user(): ValueError propagates to Phase 4 scheduler for logging — error handling is the caller's responsibility, not the orchestrator's (plan 03-02)
- services.map_pipeline is the single public API surface for Phase 4 — import run_pipeline_for_user, not sub-modules (plan 03-02)
- HTTPBearer(auto_error=False) + explicit None check — converts missing auth header to HTTP 401 (not FastAPI default 403) (plan 04-01)
- increment_interaction RPC uses INSERT...ON CONFLICT DO NOTHING then UPDATE col+1 — standard upsert resets counts to 0 (plan 04-01)
- Applied DDL via asyncpg direct connection (not MCP) — MCP requires personal access token; asyncpg with project password is equivalent (plan 04-01)

### Pending Todos

None.

### Blockers/Concerns

- Known bug: `handleLogout()` in `Home.vue` scoped inside `loadPosts()` — crashes on logout. Out of scope this milestone but worth noting.
- APScheduler single-worker constraint: multi-worker uvicorn causes double-firing. Must document clearly.
- Supabase RLS: verify service role key is used for all backend DB reads (not anon key). Verified for algorithm tables; existing match routes not yet validated.
- `psycopg2-binary` fails to build on macOS arm64 + Python 3.14. Not blocking for seed script (supabase-py uses HTTP). May need resolution before SQLAlchemy usage in later phases.

## Session Continuity

Last session: 2026-02-23
Stopped at: Completed 04-api-and-scheduler/04-01-PLAN.md. Plan 04-01 complete. Next: Phase 4 Plan 02 — interaction write endpoints (POST /interactions/like, /comment, /dm).
