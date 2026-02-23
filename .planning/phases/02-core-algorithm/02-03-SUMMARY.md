---
phase: 02-core-algorithm
plan: "03"
subsystem: map_pipeline
tags: [tdd, distance-matrix, origin-translation, tier-assignment, algorithm]
dependency_graph:
  requires:
    - 02-01  # config/algorithm.py (ALPHA, BETA, PROFILE_WEIGHTS)
    - 02-02  # interaction.py (interaction_matrix input)
  provides:
    - scoring.py (build_combined_distance_matrix)
    - origin_translator.py (translate_and_assign_tiers)
  affects:
    - 02-04  # tsne_projector output feeds into translate_and_assign_tiers
    - 03-xx  # data_fetcher.py will map location_city/state before calling scoring.py
tech_stack:
  added: []
  patterns:
    - TDD (RED → GREEN, no refactor needed)
    - Delegation to existing services/matching/scoring.py (DIST-03)
    - Stateless pure functions (ORIG-03)
    - Numpy broadcast subtraction for origin translation
key_files:
  created:
    - backend/services/map_pipeline/scoring.py
    - backend/services/map_pipeline/origin_translator.py
    - backend/tests/map_pipeline/test_scoring.py
    - backend/tests/map_pipeline/test_origin_translator.py
  modified: []
decisions:
  - "Field name mapping (city/state vs location_city/location_state) deferred to Phase 3 data_fetcher.py — UserProfile uses .city/.state, matching existing model"
  - "Tier assignment uses 2D Euclidean distance from translated coordinates, not get_ranked_matches() — avoids 0.75 max_distance cutoff that would drop outer users"
  - "_MAX_DIST=0.75 retained as a label reference constant, not a filter — all users included in output"
  - "Symmetry enforcement via (M + M.T)/2 after formula application guards against floating-point drift"
metrics:
  duration: "~2 minutes"
  completed_date: "2026-02-23"
  tasks_completed: 2
  files_created: 4
  files_modified: 0
  tests_added: 17
---

# Phase 2 Plan 03: Combined Distance Scoring and Origin Translation Summary

Combined distance matrix module and origin translation module, both fully TDD-tested. Wires profile similarity (existing matching logic) with interaction scores (Plan 02-02) and prepares per-user coordinate output for DB storage.

## What Was Built

### `backend/services/map_pipeline/scoring.py`

`build_combined_distance_matrix(users, interaction_matrix) -> np.ndarray`

Implements DIST-01 formula:
```
distance(i, j) = α × profile_distance(i, j) + β × (1 - interaction_score(i, j))
```

- Delegates profile distance to `services/matching/scoring.py` — no reimplementation (DIST-03)
- Imports `ALPHA`, `BETA`, `PROFILE_WEIGHTS` from `config/algorithm.py`
- Enforces symmetry via `(M + M.T) / 2.0` and clears diagonal explicitly
- Output: NxN ndarray, values in [0, 1], symmetric, zeros on diagonal (DIST-04)
- 7 TDD tests green

### `backend/services/map_pipeline/origin_translator.py`

`translate_and_assign_tiers(user_ids, raw_coords, requesting_user_id) -> list[dict]`

- Shifts all t-SNE coordinates by subtracting requesting user's raw position (ORIG-01)
- Requesting user appears at exactly (0.0, 0.0) as Tier 1 (ORIG-02)
- All N users (including requesting user) appear in output
- Tier assignment from 2D Euclidean distance in translated coordinate space:
  - Tier 1: 5 nearest non-requesting users (ranks 1-5)
  - Tier 2: ranks 6-15 (up to 10 users)
  - Tier 3: all remaining users (rank 16+)
- Stateless pure function — identical raw_coords with different requesting_user_id produces independent coordinate sets (ORIG-03)
- 10 TDD tests green

## Key Design Decisions

**Field Name Mapping Deferred to Phase 3**

`UserProfile` uses `.city` and `.state` fields (existing Pydantic model). Supabase DB columns are `location_city` and `location_state`. Mapping is deferred to Phase 3's `data_fetcher.py` — it will construct `UserProfile` objects with the DB values mapped to the correct fields. Changing `UserProfile` here would break existing `/match` routes.

**Tier Assignment from 2D Euclidean Distance, Not `get_ranked_matches()`**

`get_ranked_matches()` in `clustering.py` uses the precomputed distance matrix with a `max_distance=0.75` cutoff that drops users beyond the threshold. The People Map requires ALL users to appear. Instead, `translate_and_assign_tiers()` computes 2D Euclidean distances from the translated t-SNE coordinates directly — same tier boundaries (5 / 15) but no exclusion filter.

**`_MAX_DIST` Is a Label, Not a Filter**

The `_MAX_DIST = 0.75` constant is retained for reference and future use (e.g., `coord_writer.py` may use it), but the function includes all users regardless of their Euclidean distance from origin.

## Test Coverage

| Module | Test File | Tests | All Green |
|--------|-----------|-------|-----------|
| `map_pipeline/scoring.py` | `test_scoring.py` | 7 | Yes |
| `map_pipeline/origin_translator.py` | `test_origin_translator.py` | 10 | Yes |
| Full map_pipeline suite | all 4 test files | 33 | Yes |

## Deviations from Plan

None — plan executed exactly as written. All code matches the plan's provided implementations. No refactoring was needed after GREEN phase.

## Self-Check: PASSED

Files verified to exist:
- `backend/services/map_pipeline/scoring.py` — FOUND
- `backend/services/map_pipeline/origin_translator.py` — FOUND
- `backend/tests/map_pipeline/test_scoring.py` — FOUND
- `backend/tests/map_pipeline/test_origin_translator.py` — FOUND

Commits verified:
- `be368b2` — feat(02-03): implement combined distance matrix module
- `8765278` — feat(02-03): implement origin translation and tier assignment module
