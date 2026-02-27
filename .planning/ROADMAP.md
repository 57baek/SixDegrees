# Roadmap: SixDegrees

## Overview

Milestone v2.0 delivers a backend-only global coordinate map engine that replaces demo-era per-view semantics with one global map version per user, then serves request-time ego maps centered at `(0,0)` with mutual-friend filtering and safe suggestions. The phase order is dependency-driven: secure global data contract first, stable compute second, user-visible ego API compatibility third, and scheduler/rollout reliability last.

## Phases

**Phase Numbering:**
- Integer phases (20, 21, 22, 23): Planned milestone v2.0 work
- Decimal phases (20.1, 21.1): Urgent insertions if needed

- [x] **Phase 20: Global Coordinate Data Contract** - Establish one-row-per-user global coordinate semantics with secure, versioned persistence. (completed 2026-02-26)
- [x] **Phase 21: Compute Engine and Publish Validation** - Build scalable profile+interaction global embedding with fail-closed publish gates. (completed 2026-02-26)
- [x] **Phase 22: Ego Map API and Compatibility Serving** - Serve requester-centered mutual-friend maps and bounded suggestions without frontend changes. (completed 2026-02-27)
- [ ] **Phase 23: Scheduler Operations and Safe Rollout** - Run daily compute + local warm operations with duplicate protection and rollback safety.

## Phase Details

### Phase 20: Global Coordinate Data Contract
**Goal**: Users have one secure, versioned global coordinate record each, with continuity to prior position.
**Depends on**: Nothing (first phase)
**Requirements**: DATA-01, DATA-02, DATA-03, DATA-04, DATA-05, DATA-06, DATA-07, DATA-08
**Success Criteria** (what must be TRUE):
  1. A user map position is sourced from a single global coordinate row, not viewer-specific rows.
  2. After map updates, user movement remains visually continuous because exactly one prior position snapshot is retained.
  3. Map responses expose `version_date` and `computed_at`, so users and operators can verify which coordinate version is being served.
  4. Interactions foreign keys point to `profiles(id)` for both `user_id_a` and `user_id_b`, with no remaining FK dependency on `user_profiles`.
  5. Interactions are rebuilt and validated from `posts`/`likes`/`comments` for existing `profiles` users only, and all interaction IDs exist in `profiles`.
  6. Users continue to receive map data through authenticated backend paths without dependency on legacy per-view coordinate semantics.
**Plans**: 3 plans
Plans:
- [ ] 20-01-PLAN.md - Define global `map_coordinates` schema/RPC contract and global write path.
- [ ] 20-02-PLAN.md - Rebuild interactions baseline and repoint interaction FKs to `profiles(id)`.
- [ ] 20-03-PLAN.md - Wire map API/testing to global coordinates with `version_date` + `computed_at` metadata.

### Phase 21: Compute Engine and Publish Validation
**Goal**: Users get stable global map updates produced by a scalable algorithm and published only when validated.
**Depends on**: Phase 20
**Requirements**: ALGO-01, ALGO-02, ALGO-03, ALGO-04, ALGO-05
**Success Criteria** (what must be TRUE):
  1. A full global coordinate version can be generated from profile vectors plus sparse interaction refinement without dense NxN distance materialization.
  2. Between published versions, users do not experience chaotic coordinate jumps because movement is bounded by stability controls.
  3. When validation detects invalid input, unstable embedding, or persistence mismatch, the new version is blocked and the prior good version remains served.
  4. Each compute run produces auditable quality/performance diagnostics tied to the published version.
**Plans**: 2 plans
Plans:
- [ ] 21-01-PLAN.md - Build sparse embedding/refinement/stability compute core with deterministic tests.
- [ ] 21-02-PLAN.md - Add fail-closed publish validation gates and run diagnostics persistence.

### Phase 22: Ego Map API and Compatibility Serving
**Goal**: Users can open the map and reliably see a safe, viewer-centered ego map from global coordinates with no frontend changes.
**Depends on**: Phase 21
**Requirements**: EGO-01, EGO-02, EGO-03, EGO-04, EGO-05, COMP-01, COMP-02, COMP-03
**Success Criteria** (what must be TRUE):
  1. The requesting user is always returned at exact coordinate `(0,0)`.
  2. Primary visible nodes are limited to mutual friends derived from `profiles.friends` reciprocity.
  3. Returned friend nodes are translated from global coordinates into requester-centered coordinates at read time.
  4. Users with sparse/empty mutual graphs receive bounded fallback nodes marked `is_suggestion=true`, and suggestion payloads exclude sensitive fields.
  5. Existing frontend flows keep working without frontend code changes, and unauthorized cross-user map reads are denied.
**Plans**: 3 plans
Plans:
- [ ] 22-01-PLAN.md - Add safe ego-map profile projection RPC contract and SQL guard tests.
- [ ] 22-02-PLAN.md - Build deterministic ego-map projection logic (origin, mutuals, translation, suggestions).
- [ ] 22-03-PLAN.md - Wire map route + contracts for self-only auth and frontend-compatible ego serving.

### Phase 23: Scheduler Operations and Safe Rollout
**Goal**: Users receive reliable daily map updates with operational safeguards, warm delivery behavior, and rollback protection.
**Depends on**: Phase 22
**Requirements**: OPS-01, OPS-02, OPS-03, OPS-04, OPS-05, COMP-04, COMP-05
**Success Criteria** (what must be TRUE):
  1. Users receive one globally recomputed coordinate version per day at fixed UTC schedule.
  2. 7pm local-time jobs perform delivery/cache warm only and never trigger global coordinate recompute.
  3. Service restart or multi-worker edge conditions do not result in duplicate global compute execution.
  4. Version-aware warm payloads are refreshed when stale, preventing users from receiving outdated cached map responses.
  5. Likes/comments triggers are verified to maintain interactions counters correctly for insert/delete flows under current RLS and RPC setup.
  6. If v2 validation fails during rollout, users continue to receive the last known good map version via safe fallback behavior.
  7. Final milestone gate passes only when runtime and DB have zero `user_profiles` dependency, and `user_profiles` is dropped safely without data-integrity regressions.
**Plans**: 3 plans
Plans:
- [ ] 23-01-PLAN.md - Split scheduler into UTC global compute + local warm-only jobs with duplicate-run lock protection.
- [ ] 23-02-PLAN.md - Add version-aware warm cache and last-known-good fallback contract for rollout safety.
- [ ] 23-03-PLAN.md - Validate likes/comments trigger integrity and enforce fail-closed legacy `user_profiles` drop gate.

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 20. Global Coordinate Data Contract | 3/3 | Complete   | 2026-02-26 |
| 21. Compute Engine and Publish Validation | 2/2 | Complete   | 2026-02-26 |
| 22. Ego Map API and Compatibility Serving | 3/3 | Complete   | 2026-02-27 |
| 23. Scheduler Operations and Safe Rollout | 1/3 | In Progress|  |
