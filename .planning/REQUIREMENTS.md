# Requirements: SixDegrees

**Defined:** 2026-02-26
**Core Value:** A user opens the People Map and sees meaningful nearby people around themselves at (0,0), with stable daily-updated positions.

## v2.0 Requirements

Requirements for milestone v2.0 Global Coordinate Map Engine.

### Data Contract + Migration

- [x] **DATA-01**: User map positions are stored as one global current row per user in `map_coordinates`.
- [x] **DATA-02**: User map write path preserves exactly one previous coordinate snapshot (`prev_x`, `prev_y`) per user for motion continuity.
- [x] **DATA-03**: User map reads/writes do not depend on legacy per-viewer map semantics.
- [x] **DATA-04**: User map data version is explicit (`version_date`, `computed_at`) and returned in API metadata.
- [x] **DATA-05**: User map persistence/update operations are executed through secured backend data-access interfaces consistent with existing runtime patterns.
- [x] **DATA-06**: User interactions foreign keys (`user_id_a`, `user_id_b`) reference `profiles(id)` only.
- [x] **DATA-07**: User interactions table contains only user IDs that exist in `profiles`.
- [x] **DATA-08**: User interactions baseline is rebuilt from `posts`/`likes`/`comments` activity for existing `profiles` users only.

### Algorithm Engine + Validation

- [x] **ALGO-01**: User global position is computed from profile-vector manifold embedding that avoids full dense NxN distance materialization.
- [x] **ALGO-02**: User global position is refined by sparse interaction graph forces using `interactions` counts and recency weighting.
- [x] **ALGO-03**: User coordinate updates are bounded by movement-stability controls to prevent visual jitter.
- [x] **ALGO-04**: User coordinate publish is blocked when validation gates detect invalid input, unstable embedding, or persistence mismatch.
- [x] **ALGO-05**: User map compute run emits measurable quality/performance metrics and stores run-level diagnostics.

### Ego API + Suggestions

- [x] **EGO-01**: User map response always places the requesting user exactly at `(0,0)`.
- [x] **EGO-02**: User map includes only mutual friends (`profiles.friends` reciprocity) as primary visible nodes.
- [x] **EGO-03**: User map node coordinates are translated at request time from global coordinates to requester-centered coordinates.
- [x] **EGO-04**: User with empty/sparse mutual graph receives bounded fallback suggestions marked with `is_suggestion=true`.
- [x] **EGO-05**: User map response remains backward-compatible for existing frontend usage while adding non-breaking metadata fields.

### Scheduler + Operations

- [x] **OPS-01**: User global coordinates are recomputed by one daily batch schedule at fixed UTC time.
- [x] **OPS-02**: User 7pm local-time jobs perform delivery/cache warm only and never trigger global recompute.
- [x] **OPS-03**: User scheduler runtime prevents duplicate compute execution from multi-worker or restart conditions.
- [x] **OPS-04**: User cache warm path (if enabled) is version-aware and invalidates stale payloads safely.
- [x] **OPS-05**: User likes/comments triggers are validated end-to-end so interaction counters remain correct on insert/delete paths.

### Compatibility + Security

- [x] **COMP-01**: User map endpoints enforce authenticated access and prevent unauthorized cross-user map reads.
- [x] **COMP-02**: User suggestion payload excludes sensitive profile fields beyond allowed API contract.
- [x] **COMP-03**: User milestone rollout preserves existing frontend behavior without frontend code changes.
- [x] **COMP-04**: User migration and rollout path includes safe fallback/rollback behavior if v2 validation fails.
- [x] **COMP-05**: User milestone completion requires zero runtime and zero DB dependency on `user_profiles`.

### Demo and Visualization (Phase 24)

- [x] **DEMO-01**: Demo experimentation uses isolated demo tables (`demo_profiles`, `demo_interactions`, and demo map outputs) without mutating production map runtime tables.
- [x] **DEMO-02**: Demo seed flow creates exactly 100 deterministic users including Eleanor Colvin and Winston Churchill, with Eleanor configured for a 20-friend ego subset.
- [x] **DEMO-03**: Demo artifacts include baseline and amplified coordinate outputs, where Eleanor↔Winston likes/comments are increased before the amplified rerun.
- [x] **DEMO-04**: Demo notebook visualizes the global map for all 100 users.
- [x] **DEMO-05**: Demo notebook visualizes Eleanor Colvin ego subset, Eleanor-centered coordinate shift, and side-by-side before/after Eleanor maps.
- [x] **DEMO-06**: Demo workflow is reproducible from documented commands and protected by lightweight automated contract tests.

### Dynamic Sensitivity and Explainability (Phase 25)

- [x] **DYN-01**: Interaction-force scaling remains sensitivity-preserving at high interaction counts and avoids early saturation that hides strong amplification effects.
- [x] **DYN-02**: Demo pair-distance response for Eleanor<->Winston is monotonic (or near-monotonic with bounded tolerance) as amplification increases.
- [x] **DYN-03**: Demo pair nearest-neighbor rank response improves with amplification and is exported as an auditable artifact.
- [x] **DYN-04**: Dynamic sensitivity changes preserve global stability bounds (movement clipping and no runaway coordinate divergence).
- [x] **DYN-05**: Demo artifacts include force/edge diagnostics that explain observed geometric movement.
- [x] **DYN-06**: Notebook and README communicate dynamic tuning behavior, limits, and recommended presets for clear stakeholder demos.

### Profiles-Only Convergence and Sensitivity Modes (Phase 26)

- [x] **PROF-01**: Convergence path B is executed staging-first: legacy map rows are reset and one fresh global coordinate version is republished before production promotion.
- [x] **PROF-02**: Backend DB/runtime contracts operate against `profiles` only, with zero runtime dependency on `user_profiles`.
- [x] **PROF-03**: Migration path for dropping `public.user_profiles` is fail-closed and blocks on dependency/preflight violations.
- [x] **PROF-04**: Demo sensitivity modes are selectable as `natural`, `strong-bounded`, and `uncapped`, with `natural` preserving current bounded defaults.
- [x] **PROF-05**: CLI exposes tunable amplification and sensitivity knobs, and exports metadata that allows observing Eleanor/Winston distance and rank changes.
- [x] **PROF-06**: Verification proves monotonic movement improvements in demo modes and no regressions in natural mode.

## Future Requirements

Deferred to future milestones.

### Discovery and Product Expansion

- **DISC-01**: User map suggestions include explainable "why shown" factors.
- **DISC-02**: User map updates support near-real-time incremental recompute.
- **DISC-03**: User receives push/in-app map update notifications.

### Platform Scale Evolution

- **SCALE-01**: User global compute runs in dedicated worker/service topology when scale thresholds are exceeded.
- **SCALE-02**: User map serving path supports advanced cache distribution and hot-shard mitigation.

## Out of Scope

Explicitly excluded for v2.0.

| Feature | Reason |
|---------|--------|
| Frontend code changes | Locked scope from milestone context |
| `profiles` schema changes | Locked constraint to preserve frontend compatibility |
| `pending_requests` table changes | Explicitly excluded by milestone constraints |
| Migrating legacy `user_profiles` users into `profiles` | Explicit decision: only existing `profiles` users are in v2 runtime scope |
| New follow-system product rollout | Not required for v2.0 map backend milestone |
| Push notification delivery infrastructure | Deferred until backend map engine is stable |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| DATA-01 | Phase 20 | Complete |
| DATA-02 | Phase 20 | Complete |
| DATA-03 | Phase 20 | Complete |
| DATA-04 | Phase 20 | Complete |
| DATA-05 | Phase 20 | Complete |
| DATA-06 | Phase 20 | Complete |
| DATA-07 | Phase 20 | Complete |
| DATA-08 | Phase 20 | Complete |
| ALGO-01 | Phase 21 | Complete |
| ALGO-02 | Phase 21 | Complete |
| ALGO-03 | Phase 21 | Complete |
| ALGO-04 | Phase 21 | Complete |
| ALGO-05 | Phase 21 | Complete |
| EGO-01 | Phase 22 | Complete |
| EGO-02 | Phase 22 | Complete |
| EGO-03 | Phase 22 | Complete |
| EGO-04 | Phase 22 | Complete |
| EGO-05 | Phase 22 | Complete |
| OPS-01 | Phase 23 | Complete |
| OPS-02 | Phase 23 | Complete |
| OPS-03 | Phase 23 | Complete |
| OPS-04 | Phase 23 | Complete |
| OPS-05 | Phase 23 | Complete |
| COMP-01 | Phase 22 | Complete |
| COMP-02 | Phase 22 | Complete |
| COMP-03 | Phase 22 | Complete |
| COMP-04 | Phase 23 | Complete |
| COMP-05 | Phase 23 | Complete |
| DEMO-01 | Phase 24 | Complete |
| DEMO-02 | Phase 24 | Complete |
| DEMO-03 | Phase 24 | Complete |
| DEMO-04 | Phase 24 | Complete |
| DEMO-05 | Phase 24 | Complete |
| DEMO-06 | Phase 24 | Complete |
| DYN-01 | Phase 25 | Planned |
| DYN-02 | Phase 25 | Planned |
| DYN-03 | Phase 25 | Planned |
| DYN-04 | Phase 25 | Planned |
| DYN-05 | Phase 25 | Planned |
| DYN-06 | Phase 25 | Planned |
| PROF-01 | Phase 26 | Planned |
| PROF-02 | Phase 26 | Complete |
| PROF-03 | Phase 26 | Planned |
| PROF-04 | Phase 26 | Planned |
| PROF-05 | Phase 26 | Planned |
| PROF-06 | Phase 26 | Complete |

**Coverage:**
- Total requirements: 46
- Mapped to phases: 46
- Unmapped: 0 ✓

---
*Requirements defined: 2026-02-26*
*Last updated: 2026-02-27 after adding Phase 26 profiles-only convergence and sensitivity-mode requirements*
