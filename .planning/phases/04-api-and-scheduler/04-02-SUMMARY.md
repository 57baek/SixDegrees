---
phase: 04-api-and-scheduler
plan: 02
subsystem: api
tags: [fastapi, supabase, map-coordinates, tsne, apiRouter]

# Dependency graph
requires:
  - phase: 03-pipeline-integration
    provides: run_pipeline_for_user() public API in services.map_pipeline.__init__
  - phase: 01-database-foundation
    provides: map_coordinates and user_profiles tables in Supabase
provides:
  - GET /map/{user_id} — reads precomputed coordinates from DB, 404 on miss
  - POST /map/trigger/{user_id} — triggers pipeline for a user, returns updated coordinates
affects: [04-03, 04-04, 05-demo-and-docs]

# Tech tracking
tech-stack:
  added: []
  patterns: [shared helper _fetch_map_response() for deduplication, single .in_() query for display_names]

key-files:
  created:
    - backend/routes/map.py
  modified: []

key-decisions:
  - "POST /map/trigger/{user_id} requires no JWT — used for testing/demo only, per CONTEXT.md locked decision"
  - "ValueError from run_pipeline_for_user() mapped to HTTP 422 — conveys semantic failure (pipeline constraint not met)"
  - "_fetch_map_response() shared helper eliminates query duplication between GET and POST endpoints"
  - "display_name fetched via single .in_() query after collecting all other_user_ids — no N+1 queries"

patterns-established:
  - "Shared helper pattern: _fetch_map_response() used by both endpoints rather than duplicated query logic"
  - "ValueError → HTTP 422 mapping for pipeline domain errors (N < 10, user not found)"

requirements-completed: [API-01, API-02, API-03, API-04, API-05]

# Metrics
duration: 2min
completed: 2026-02-23
---

# Phase 4 Plan 02: Map API Endpoints Summary

**FastAPI GET /map/{user_id} and POST /map/trigger/{user_id} reading precomputed t-SNE coordinates from Supabase with single-query display_name enrichment**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-02-23T16:03:43Z
- **Completed:** 2026-02-23T16:05:06Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- GET /map/{user_id} queries map_coordinates for current rows and enriches with display_name in one .in_() call
- POST /map/trigger/{user_id} triggers run_pipeline_for_user() and returns updated coordinates in same response shape
- 404 with exact message "Map not yet computed for this user" on empty result
- ValueError from pipeline (N < 10, user not found) mapped to HTTP 422

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement GET /map/{user_id} and POST /map/trigger/{user_id}** - `3fbc84f` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified
- `backend/routes/map.py` - Two map endpoints with _fetch_map_response() shared helper

## Decisions Made
- POST /map/trigger/{user_id} has no JWT requirement — per CONTEXT.md locked decision for testing/demo use
- ValueError from run_pipeline_for_user() returns HTTP 422 (Unprocessable Entity) to communicate semantic failure (too few users or user not found)
- _fetch_map_response() helper extracted to avoid duplicated query logic between both endpoints

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- GET /map/{user_id} and POST /map/trigger/{user_id} are live and importable
- router exported from backend/routes/map.py — ready to register in app.py
- Interaction write endpoints (POST /interactions/like, /comment, /dm) are next: Plan 04-03

---
*Phase: 04-api-and-scheduler*
*Completed: 2026-02-23*
