---
phase: 01-database-foundation
plan: "01"
subsystem: database
tags: [supabase, postgresql, ddl, rls, uuid, tsne-pipeline]

# Dependency graph
requires: []
provides:
  - "user_profiles table DDL (12 columns, UUID PK, interests TEXT[], timezone TEXT)"
  - "interactions table DDL (composite PK user_id_a/user_id_b, canonical pair order CHECK)"
  - "map_coordinates table DDL (is_current BOOLEAN versioning, tier CHECK 1/2/3)"
  - "composite index idx_map_coordinates_center_is_current for fast API reads"
  - "RLS enabled on all 3 tables (service role key bypasses; anon key blocked)"
  - "Idempotent FK constraints on interactions referencing user_profiles"
affects:
  - 01-database-foundation
  - 02-algorithm-pipeline
  - 03-pipeline-integration
  - 04-api-endpoints

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "CREATE TABLE IF NOT EXISTS for idempotent DDL"
    - "DO $$ BEGIN ... END $$; block for idempotent ALTER TABLE constraint additions"
    - "Canonical pair ordering (user_id_a < user_id_b) for interaction deduplication"
    - "is_current BOOLEAN versioning for map_coordinates (retain old rows for animation delta)"

key-files:
  created:
    - backend/sql/setup_tables.sql
  modified: []

key-decisions:
  - "No FK from user_profiles.user_id to auth.users — seed users won't exist in auth.users"
  - "Canonical pair ordering enforced by CHECK constraint, not application logic"
  - "FK constraints wrapped in DO block for idempotency on re-run"
  - "RLS enabled on all tables; service role key bypasses, anon key blocked"

patterns-established:
  - "Idempotent DDL pattern: IF NOT EXISTS + DO block for constraints"
  - "map_coordinates versioning: mark old rows is_current=false, insert new rows, never delete"

requirements-completed:
  - DB-01
  - DB-02
  - DB-03
  - DB-04

# Metrics
duration: ~5min
completed: 2026-02-22
---

# Phase 1 Plan 01: Database Foundation - DDL Setup Summary

**Three Supabase tables (user_profiles, interactions, map_coordinates) with composite index, RLS, and idempotent FK constraints via a single re-runnable SQL script**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-02-22T23:20:00Z (estimated)
- **Completed:** 2026-02-22T23:41:59Z
- **Tasks:** 1 of 2 complete (Task 2 awaiting human action — applying SQL in Supabase dashboard)
- **Files modified:** 1

## Accomplishments
- Created `backend/sql/setup_tables.sql` with all DDL for the three pipeline tables
- All 3 CREATE TABLE statements use IF NOT EXISTS for safe re-runs
- Composite index `idx_map_coordinates_center_is_current` created for fast Phase 4 API reads
- RLS enabled on all 3 tables — service role key bypasses, anon key blocked
- FK constraints on interactions table wrapped in idempotent DO $$ block

## Task Commits

Each task was committed atomically:

1. **Task 1: Write setup_tables.sql DDL script** - `1f30f89` (feat)

**Plan metadata:** pending (awaiting Task 2 human action completion)

## Files Created/Modified
- `backend/sql/setup_tables.sql` - Complete DDL for user_profiles, interactions, map_coordinates tables + composite index + RLS + idempotent FK constraints

## Decisions Made
- No FK from `user_profiles.user_id` to `auth.users` — seed data users won't exist in Supabase Auth, so this FK would block seed inserts
- FK constraints on `interactions` referencing `user_profiles` are wrapped in an idempotent `DO $$` block so the script can be re-run safely even after tables exist
- Canonical pair ordering (user_id_a < user_id_b) enforced at DB level with CHECK constraint, not application logic

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

**Manual database setup required.** Apply `backend/sql/setup_tables.sql` in the Supabase dashboard:

1. Open Supabase project dashboard
2. Navigate to SQL Editor (left sidebar)
3. Click "New query"
4. Copy entire contents of `backend/sql/setup_tables.sql`
5. Paste into the SQL editor
6. Click "Run" (or Ctrl+Enter)
7. Expected: "Success. No rows returned" for each statement
8. Verify in Table Editor: user_profiles, interactions, map_coordinates all appear
9. Verify in Database > Indexes: idx_map_coordinates_center_is_current on map_coordinates

After tables exist, verify service role key access (run from `backend/` with venv activated):
```bash
python -c "
import sys; sys.path.insert(0, '.')
from config.supabase import get_supabase_client
sb = get_supabase_client()
for t in ['user_profiles', 'interactions', 'map_coordinates']:
    r = sb.table(t).select('*').limit(1).execute()
    print(f'{t}: OK')
"
```
Expected: all three print "OK" with no exceptions.

## Next Phase Readiness
- `backend/sql/setup_tables.sql` is ready to apply — no changes needed
- Once tables are live, Phase 1 Plan 02 (seed data) can proceed
- Phase 2 (algorithm pipeline) depends on `user_profiles`, `interactions`, and `map_coordinates` existing with these exact schemas

---
*Phase: 01-database-foundation*
*Completed: 2026-02-22*
