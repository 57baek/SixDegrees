# Phase 22 Research: Ego Map API and Compatibility Serving

**Date:** 2026-02-26
**Scope:** EGO-01, EGO-02, EGO-03, EGO-04, EGO-05, COMP-01, COMP-02, COMP-03

## What Exists Today

- `backend/routes/map.py` reads global coordinates via `get_global_map_coordinates`, returns raw global rows, and does not perform ego-centering or mutual-friend filtering.
- `GET /map/{user_id}` is JWT-protected but currently allows any authenticated user to request any `user_id` map payload.
- Map payload contract currently includes top-level `user_id`, `version_date`, `computed_at`, and `coordinates[]` entries with `user_id`, `x`, `y`, `tier`, `nickname`.
- Pipeline publish path in `backend/services/map_pipeline/__init__.py` already maintains global coordinate consistency and metadata (`version_date`, `computed_at`).

## Gap to Phase Goal

Phase 22 requires read-time transformation from global coordinates into requester-centered ego map semantics while preserving frontend compatibility:

1. Requesting user must always be exactly `(0,0)` in responses.
2. Primary visible nodes must be reciprocal friends (mutuality from `profiles.friends`).
3. Returned coordinates must be translated relative to requester's global position at read time.
4. Sparse/empty mutual graphs must receive bounded fallback suggestions (`is_suggestion=true`) with safe payload shape.
5. Existing frontend flow must keep working without frontend edits; unauthorized cross-user reads must be denied.

## Recommended Technical Direction

### 1) Add a dedicated ego-map projection module

- Create a pure transformation module (e.g., `backend/services/map_pipeline/ego_map.py`) that accepts global coordinate rows + profile projection rows and returns API-ready ego coordinates.
- Keep this module deterministic and free of Supabase I/O so it can be unit-tested with fixed fixtures.

Why: isolates business logic (mutual filtering, translation, suggestion selection) from route plumbing and improves testability.

### 2) Use a minimal profile projection for serving

- Add/ensure RPC read contract used by map route returns only fields required for ego serving and safe suggestions (ID, nickname, friends, and any explicitly allowed display metadata).
- Avoid using full profile payloads in suggestion output.

Why: satisfies COMP-02 (sensitive field exclusion) while reducing accidental contract leakage.

### 3) Enforce self-only map reads at API boundary

- In `GET /map/{user_id}`, compare `acting_user_id` from JWT dependency to `user_id` path param and return `403` on mismatch.
- Keep trigger endpoint self-only behavior unchanged.

Why: satisfies COMP-01 and aligns with phase requirement that unauthorized cross-user reads are denied.

### 4) Preserve response compatibility while extending metadata safely

- Keep current top-level map keys (`user_id`, `version_date`, `computed_at`, `coordinates`).
- Keep coordinate entries backward-compatible (`user_id`, `x`, `y`, `tier`, `nickname`) and add non-breaking `is_suggestion` flag.

Why: satisfies EGO-05 and COMP-03 without frontend changes.

## File-Level Impact (Expected)

- Add SQL contract for profile projection RPC used by map-serving path.
- Add pure ego-map projection service with deterministic tests.
- Update `backend/routes/map.py` to call ego projection and enforce self-only reads.
- Update endpoint contract tests and fixtures in `backend/tests/conftest.py` + `backend/tests/test_contracts.py`.

## Common Pitfalls to Avoid

- Translating all points but forgetting to force requester to exact `(0,0)` (floating drift).
- Treating one-way friend links as mutual.
- Building suggestion payloads from full profile records and leaking fields not in API contract.
- Breaking existing coordinate shape or top-level map metadata required by frontend.
- Returning 200 with empty/invalid payload for unauthorized cross-user reads instead of explicit 403.

## Validation Architecture

Plan-level verification should prove five truths:

1. **Ego origin truth:** requester node is exactly `(0,0)` in all successful map responses.
2. **Mutuality truth:** primary nodes are reciprocal friends only.
3. **Translation truth:** non-requester coordinates are returned as `global - requester_global`.
4. **Fallback truth:** sparse/empty mutual graph receives bounded `is_suggestion=true` nodes with safe fields only.
5. **Compatibility/security truth:** existing route contract remains usable by frontend and cross-user read attempts are denied.

Recommended automated checks:

- `cd backend && ./venv/bin/python -m pytest -q tests/map_pipeline/test_ego_map.py`
- `cd backend && ./venv/bin/python -m pytest -q tests/test_contracts.py -k map`
- `cd backend && ./venv/bin/python -m pytest -q tests/test_phase22_ego_profile_projection_sql.py`
