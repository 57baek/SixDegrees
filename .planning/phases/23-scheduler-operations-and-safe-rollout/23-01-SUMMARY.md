---
phase: 23-scheduler-operations-and-safe-rollout
plan: 01
subsystem: infra
tags: [apscheduler, supabase-rpc, scheduler, dedupe-lock, map-pipeline]
requires:
  - phase: 22-compatibility-and-ego-map-integration
    provides: global map serving compatibility and deterministic pipeline contracts
provides:
  - Global UTC compute scheduler job with explicit lock-guarded entrypoint
  - Local 19:00 timezone warm-only scheduler jobs that do not recompute coordinates
  - Deterministic scheduler lock and registration regression tests
affects: [scheduler-operations, rollout-safety, map-pipeline-runtime]
tech-stack:
  added: []
  patterns: [supabase-rpc-locking, split-scheduler-job-families, deterministic-job-registration-tests]
key-files:
  created:
    - backend/services/map_pipeline/scheduler_lock.py
  modified:
    - backend/services/map_pipeline/scheduler.py
    - backend/tests/map_pipeline/test_scheduler.py
key-decisions:
  - "Use a dedicated Supabase RPC lock key with owner token and TTL to prevent duplicate global compute entry."
  - "Run exactly one daily global compute at 00:00 UTC and reserve timezone jobs for warm-only refresh behavior."
patterns-established:
  - "Scheduler split pattern: one UTC recompute job + per-timezone warm-only jobs."
  - "Dedupe guard pattern: acquire lock before global run, skip on contention, release in finally."
requirements-completed: [OPS-01, OPS-02, OPS-03]
duration: 4min
completed: 2026-02-27
---

# Phase 23 Plan 01: Scheduler Operations and Safe Rollout Summary

**APScheduler now runs one UTC global recompute guarded by a Supabase-backed dedupe lock while 19:00 local timezone jobs are warm-only and non-recompute.**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-27T01:20:03Z
- **Completed:** 2026-02-27T01:24:17Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Added `scheduler_lock.py` with stable acquire/release APIs using RPC lock key, TTL, and owner token semantics.
- Refactored scheduler registration into one fixed daily UTC global compute job plus per-timezone 19:00 warm-only jobs.
- Added deterministic scheduler tests for lock acquisition/contestion, warm-only behavior, global dedupe skip path, and release-on-error behavior.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add scheduler dedupe lock contract and unit coverage** - `9085361` (feat)
2. **Task 2: Refactor scheduler into UTC global compute and local warm-only jobs** - `3d2d945` (feat)

## Files Created/Modified
- `backend/services/map_pipeline/scheduler_lock.py` - Supabase RPC-backed global compute lock helpers with TTL and owner token support.
- `backend/services/map_pipeline/scheduler.py` - global compute job, warm-only timezone jobs, and dedupe lock guard integration.
- `backend/tests/map_pipeline/test_scheduler.py` - lock and scheduler registration/behavior regression coverage.

## Decisions Made
- Select a deterministic anchor user (sorted lowest profile id) for the once-per-day global compute entrypoint.
- Keep duplicate-prevention explicit at scheduler entry by logging contention and skipping compute when lock acquisition fails.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed lock release-path test monkeypatch target**
- **Found during:** Task 1 (Add scheduler dedupe lock contract and unit coverage)
- **Issue:** The release-path test monkeypatched module functions, but local imports bypassed the patch and triggered a live RPC call.
- **Fix:** Switched the test helper to call `scheduler_lock.acquire_global_compute_lock` and `scheduler_lock.release_global_compute_lock` via module references so monkeypatching applies correctly.
- **Files modified:** `backend/tests/map_pipeline/test_scheduler.py`
- **Verification:** `cd backend && ./venv/bin/python -m pytest -q tests/map_pipeline/test_scheduler.py -k "lock"`
- **Committed in:** `9085361` (part of Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Fix was necessary for deterministic offline tests; no scope creep.

## Issues Encountered
- None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Scheduler now enforces daily recompute cadence and duplicate-entry guard required by rollout operations.
- Ready for phase plans that add warm payload versioning and rollback-safe runtime behaviors.

---
*Phase: 23-scheduler-operations-and-safe-rollout*
*Completed: 2026-02-27*

## Self-Check: PASSED
