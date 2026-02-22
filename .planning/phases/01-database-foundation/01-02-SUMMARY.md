---
phase: 01-database-foundation
plan: "02"
subsystem: database
tags: [supabase, postgresql, seed-data, python, tsne-pipeline]

# Dependency graph
requires:
  - phase: 01-01
    provides: "user_profiles, interactions, map_coordinates tables live in Supabase with correct schema"
provides:
  - "20 diverse mock users in user_profiles across 5 interest clusters (outdoors, creative, tech/gaming, social/food, sports)"
  - "35 seeded interaction pairs in interactions with canonical pair ordering (user_id_a < user_id_b)"
  - "6 distinct timezones present (America/Chicago, America/Denver, America/Los_Angeles, America/New_York, Asia/Tokyo, Europe/London)"
  - "backend/scripts/seed_db.py — idempotent seed script via upsert on_conflict"
affects:
  - 02-algorithm-pipeline
  - 03-pipeline-integration

# Tech tracking
tech-stack:
  added:
    - "supabase-py 2.28.0 (installed in venv for seed script usage)"
    - "python-dotenv 1.2.1"
  patterns:
    - "canonical_pair() helper enforces user_id_a < user_id_b before every interaction insert"
    - "Hardcoded UUID strings in USER_DATA list for idempotent upserts on re-run"
    - "sys.path.insert(0, ...) pattern for scripts that run from any directory"
    - "upsert with on_conflict for both tables — never insert, always upsert"

key-files:
  created:
    - backend/scripts/seed_db.py
  modified: []

key-decisions:
  - "Column names are location_city/location_state (not city/state) — matches DDL from plan 01-01"
  - "Hardcoded UUIDs (not uuid.uuid4() at runtime) to guarantee idempotent upserts on re-run"
  - "35 interaction pairs: 6 intra-cluster per cluster (5x6=30) + 5 sparse cross-cluster — designed to produce visible cluster separation in t-SNE"

patterns-established:
  - "Seed script pattern: sys.path.insert + config import + hardcoded UUIDs + upsert"
  - "canonical_pair() as helper before every interaction row construction"

requirements-completed:
  - DB-05

# Metrics
duration: ~4min
completed: 2026-02-22
---

# Phase 1 Plan 02: Seed Data - Summary

**Idempotent seed script populating 20 diverse users across 5 t-SNE-visible interest clusters and 35 canonical-ordered interaction pairs across 6 timezones**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-02-22T23:48:25Z
- **Completed:** 2026-02-22T23:52:30Z
- **Tasks:** 2 of 2 complete
- **Files modified:** 1

## Accomplishments

- Created `backend/scripts/` directory and wrote `seed_db.py` with 20 hardcoded-UUID users across 5 interest clusters
- Seeded 35 interaction pairs using `canonical_pair()` helper ensuring `user_id_a < user_id_b` on every row
- Script runs idempotently — second run produces identical row counts without errors
- 6 distinct timezones seeded (exceeds the >= 4 requirement for Phase 4 scheduler)
- Phase 1 complete: all 3 tables exist, seeded, and verified

## Task Commits

Each task was committed atomically:

1. **Task 1: Write seed_db.py with 20 diverse users and interaction pairs** - `8177309` (feat)
2. **Task 2: Run seed script and verify data in Supabase** - `23930f2` (fix — column name bug auto-corrected)

## Files Created/Modified

- `backend/scripts/seed_db.py` - Idempotent seed script: 20 users in 5 clusters + 35 interaction pairs with canonical pair ordering

## Decisions Made

- Column names `location_city` / `location_state` used (not `city` / `state`) — discovered by running the script and reading the PGRST204 error; matches the DDL from plan 01-01 which uses `location_city`/`location_state`
- Hardcoded UUID strings rather than generating at runtime, so upserts resolve to the same primary keys on every re-run

## Timezone Distribution

| Timezone | Users |
|----------|-------|
| America/Chicago | 5 (Taylor Kim, Casey Brown, Avery Johnson, Riley Davis, Cameron White, Emery Hall) |
| America/Denver | 2 (Alex Rivera, Jordan Lee) |
| America/Los_Angeles | 3 (Sam Park, Morgan Chen, Quinn Wilson, Drew Martinez) |
| America/New_York | 6 (Jamie Garcia, Logan Anderson, Peyton Harris, Blake Robinson, Parker Lewis) |
| Asia/Tokyo | 1 (Skyler Thompson) |
| Europe/London | 2 (Reese Jackson, Hayden Walker) |

## Interest Cluster Structure

| Cluster | Users | Primary Interests |
|---------|-------|-------------------|
| Outdoors | 4 | hiking, camping, photography, rock climbing |
| Creative | 4 | music, concerts, painting, film |
| Tech/Gaming | 4 | gaming, programming, anime, sci-fi |
| Social/Food | 4 | cooking, travel, wine, yoga |
| Sports | 4 | soccer, basketball, fitness, running |

5 sparse cross-cluster interaction pairs provide natural overlap for interesting intermediate t-SNE positioning.

## Idempotency Confirmed

Second run output:
```
=== SixDegrees Seed Script ===
Seeding 20 users...
  Seeded 20 user_profiles rows
Seeding 35 interaction pairs...
  Seeded 35 interaction rows

Verification:
  user_profiles: 20 rows
  interactions:  35 rows
  Distinct timezones: ['America/Chicago', 'America/Denver', 'America/Los_Angeles', 'America/New_York', 'Asia/Tokyo', 'Europe/London']

Seed complete. All assertions passed.
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed column names city/state to location_city/location_state**
- **Found during:** Task 2 (Run seed script and verify data in Supabase)
- **Issue:** Initial seed script used `city` and `state` as dict keys but the `user_profiles` table DDL (from plan 01-01) defines these columns as `location_city` and `location_state`. Supabase returned `PGRST204: Could not find the 'city' column`
- **Fix:** Renamed all 20 user dict entries from `city`/`state` to `location_city`/`location_state`
- **Files modified:** `backend/scripts/seed_db.py`
- **Verification:** Script ran successfully after fix; 20 rows seeded and verified
- **Committed in:** `23930f2` (fix commit, combined with Task 2 verification)

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug)
**Impact on plan:** Necessary correction — column names in seed script must match live DDL. No scope creep.

## Issues Encountered

- `psycopg2-binary` failed to build from source on macOS arm64/Python 3.14. Not needed for seed script (supabase-py uses HTTP, not direct psycopg2). Installed only `supabase` and `python-dotenv` for this plan; full `requirements.txt` install can be attempted once a compatible psycopg2 build is available or the dependency is removed/replaced.

## Next Phase Readiness

- All 3 tables live: `user_profiles` (20 rows), `interactions` (35 rows), `map_coordinates` (0 rows, correct)
- Phase 1 is complete — database foundation fully established
- Phase 2 (algorithm pipeline) can begin: `data_fetcher.py` will read the seeded `user_profiles` + `interactions` rows
- Power pair Quinn Wilson / Drew Martinez (15 likes, 9 comments, 4 DMs) tests the 95th-percentile clipping in Phase 2 `interaction.py`

---
*Phase: 01-database-foundation*
*Completed: 2026-02-22*

## Self-Check: PASSED

- FOUND: backend/scripts/seed_db.py
- FOUND: .planning/phases/01-database-foundation/01-02-SUMMARY.md
- FOUND commit: 8177309 (feat: write seed_db.py)
- FOUND commit: 23930f2 (fix: column name correction + verified seed run)
