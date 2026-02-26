---
phase: 21-compute-engine-and-publish-validation
plan: 01
subsystem: api
tags: [map-pipeline, sparse-embedding, stability, pytest]
requires:
  - phase: 20-global-coordinate-data-contract
    provides: global map coordinate persistence and map metadata contract
provides:
  - sparse profile embedding stage without dense NxN production precompute
  - sparse interaction refinement with recency-weighted pulls
  - alignment and bounded movement clipping before origin translation
affects: [phase-22-ego-map-serving, phase-23-scheduler-rollout]
tech-stack:
  added: []
  patterns:
    - typed stage contracts for embedding/refinement/stability
    - sparse edge-based coordinate refinement loop
    - prior-anchor alignment plus per-user max-delta clipping
key-files:
  created:
    - backend/services/map_pipeline/contracts.py
    - backend/services/map_pipeline/sparse_embedding.py
    - backend/services/map_pipeline/interaction_refinement.py
    - backend/services/map_pipeline/stability.py
    - backend/tests/map_pipeline/test_sparse_embedding.py
    - backend/tests/map_pipeline/test_interaction_refinement.py
    - backend/tests/map_pipeline/test_stability.py
  modified:
    - backend/services/map_pipeline/pipeline.py
key-decisions:
  - "Use sparse profile vectors plus k-NN graph extraction to avoid dense NxN precompute in the pipeline path."
  - "Apply interaction refinement as iterative sparse edge pulls with exponential recency decay from optional days-since fields."
  - "Expose optional prior anchors in run_pipeline and enforce per-user movement clipping through a dedicated stability stage."
patterns-established:
  - "Sparse stage orchestration: embedding -> interaction refinement -> stability -> origin translation"
  - "Movement continuity guardrails are applied before translated map payload generation"
requirements-completed: [ALGO-01, ALGO-02, ALGO-03]
duration: 5min
completed: 2026-02-26
---

# Phase 21 Plan 01: Build sparse embedding/refinement/stability compute core with deterministic tests Summary

**Sparse profile manifold embedding now feeds recency-weighted interaction refinement and prior-aligned movement clipping while preserving existing pipeline output keys.**

## Performance

- **Duration:** 5 min
- **Started:** 2026-02-26T23:11:36Z
- **Completed:** 2026-02-26T23:16:21Z
- **Tasks:** 3
- **Files modified:** 8

## Accomplishments
- Added exported typed contracts for sparse embedding, interaction refinement, and stability stage I/O.
- Replaced dense pipeline stages in `run_pipeline` with sparse embedding, recency-weighted refinement, and bounded stability alignment.
- Added deterministic tests validating sparse edge behavior, recency influence on refinement distance, and max-delta clipping.

## Task Commits

Each task was committed atomically:

1. **Task 1: Define sparse compute contracts** - `36f3b23` (feat)
2. **Task 2: Implement sparse embedding, interaction refinement, and stability stages** - `a94171c` (feat)
3. **Task 3: Add deterministic unit tests for sparse and stability behavior** - `1961777` (test)

**Plan metadata:** `d2fcda0` (docs)

## Files Created/Modified
- `backend/services/map_pipeline/contracts.py` - Stage contracts for sparse edge data, inputs, outputs, and stability metrics.
- `backend/services/map_pipeline/sparse_embedding.py` - Sparse profile vector embedding and k-NN edge extraction.
- `backend/services/map_pipeline/interaction_refinement.py` - Sparse interaction edge weighting with recency decay and iterative coordinate pulls.
- `backend/services/map_pipeline/stability.py` - Prior-anchor alignment, per-user movement clipping, and stability metric calculation.
- `backend/services/map_pipeline/pipeline.py` - Orchestrates sparse stages while preserving `raw_coords`, `translated_results`, and `user_ids` contract.
- `backend/tests/map_pipeline/test_sparse_embedding.py` - Deterministic sparse embedding behavior and non-dense edge coverage.
- `backend/tests/map_pipeline/test_interaction_refinement.py` - Recency-weighted interaction refinement distance assertions.
- `backend/tests/map_pipeline/test_stability.py` - Max movement clipping and metrics assertions.

## Decisions Made
- Shifted stage boundaries to typed contract objects so sparse modules can be composed without untyped dict blobs.
- Chose sparse feature vector + k-NN graph extraction for profile stage to satisfy no dense NxN requirement in production flow.
- Made stability optional via `prior_coordinates` input so existing callers remain compatible while enabling bounded movement when anchors are available.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Pytest command failed outside backend virtualenv**
- **Found during:** Task 1 (Define sparse compute contracts)
- **Issue:** `python3 -m pytest` failed with "No module named pytest" in system interpreter.
- **Fix:** Executed verification using backend virtualenv interpreter (`./venv/bin/python -m pytest ...`).
- **Files modified:** None
- **Verification:** Required task and final verification tests all passed via virtualenv runner.
- **Committed in:** N/A (execution environment adjustment only)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** No scope change; verification path corrected to project runtime environment.

## Auth Gates
None.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Sparse compute core is in place and covered by deterministic unit tests.
- Ready for 21-02 publish-gate and diagnostics persistence work.

## Self-Check: PASSED
- Verified created files exist on disk.
- Verified task commits `36f3b23`, `a94171c`, and `1961777` exist in git history.

---
*Phase: 21-compute-engine-and-publish-validation*
*Completed: 2026-02-26*
