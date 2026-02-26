# Architecture Research

**Domain:** v2.0 global coordinate map engine integration (FastAPI + Supabase)
**Researched:** 2026-02-26
**Confidence:** HIGH

## Standard Architecture

### System Overview

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ API Layer (FastAPI)                                                         │
├──────────────────────────────────────────────────────────────────────────────┤
│  /map/{user_id} (compat)   /map/trigger/{user_id} (compat trigger)         │
│          │                               │                                   │
│          └──────────────┬────────────────┘                                   │
├──────────────────────────────────────────────────────────────────────────────┤
│ Map Application Services (new facade + validators)                          │
├──────────────────────────────────────────────────────────────────────────────┤
│  ego_map_service     global_run_service     validation_gate_service          │
│       │                     │                         │                       │
├───────┴─────────────────────┴─────────────────────────┴──────────────────────┤
│ Pipeline Core (batch compute)                                                │
├──────────────────────────────────────────────────────────────────────────────┤
│  profile_feature_builder -> umap_embedder -> sparse_refiner -> coord_writer │
│                                  │                    │                       │
│                                  └──── uses interactions graph (sparse E)    │
├──────────────────────────────────────────────────────────────────────────────┤
│ Data Access (Supabase RPC boundary)                                          │
├──────────────────────────────────────────────────────────────────────────────┤
│  read_profiles  read_interactions  read_map_global  upsert_map_global       │
│  read_mutual_friends  read_nearest_suggestions  write_validation_audit       │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities (new vs modified)

| Component | Responsibility | Typical Implementation | Status |
|-----------|----------------|------------------------|--------|
| `backend/routes/map.py` | Keep external API contract stable; delegate to new map facade | FastAPI router + existing auth dependency | **Modified** |
| `backend/services/map_pipeline/` (existing) | Legacy per-view pipeline (kept during migration window) | Existing orchestrator/stages | **Unchanged initially, then deprecated** |
| `backend/services/map_v2/facade.py` | Single entrypoint for route read/trigger operations | Thin app-service layer routing to ego/global services | **New** |
| `backend/services/map_v2/global_pipeline.py` | Batch global run orchestration (fetch -> embed -> refine -> validate -> persist) | Pure stage composition + I/O adapters | **New** |
| `backend/services/map_v2/feature_builder.py` | Build profile vectors from canonical `profiles` fields | Deterministic feature matrix builder | **New** |
| `backend/services/map_v2/umap_projector.py` | Stage A embedding from vectors (no NxN matrix) | `umap.UMAP(metric='cosine', random_state=42, ...)` | **New** |
| `backend/services/map_v2/interaction_refiner.py` | Stage B sparse interaction refinement with movement clamp | Iterative sparse graph force update | **New** |
| `backend/services/map_v2/ego_query.py` | Request-time map translation and friend filtering | Mutual-friend resolver + coordinate translation | **New** |
| `backend/services/map_v2/validators.py` | Validation gates before write + before response | Data, algorithm, persistence, contract checks | **New** |
| `backend/services/map_pipeline/scheduler.py` | Register daily global compute and optional 7pm cache warm | APScheduler `AsyncIOScheduler` + `CronTrigger` | **Modified** |
| `backend/sql/*v2*.sql` | Repurpose `map_coordinates` to one-row-per-user schema and RPCs | Idempotent SQL migrations + RPC wrappers | **New** |

## Recommended Project Structure

```
backend/
├── routes/
│   └── map.py                          # keep endpoint shapes; swap internals to facade
├── services/
│   ├── map_pipeline/                   # legacy v1 pipeline (kept until cutover complete)
│   └── map_v2/
│       ├── facade.py                   # route-facing adapter
│       ├── global_pipeline.py          # batch orchestrator
│       ├── feature_builder.py          # profile vectorization
│       ├── umap_projector.py           # stage A embedding
│       ├── interaction_refiner.py      # stage B sparse refinement
│       ├── ego_query.py                # request-time ego map path
│       ├── suggestions.py              # nearest non-friend fallback
│       ├── persistence.py              # read/write RPC wrappers
│       └── validators.py               # run gates and response gates
├── services/map_pipeline/scheduler.py  # keep file; register v2 jobs by feature flag
└── tests/
    ├── map_pipeline/                   # existing tests (legacy)
    └── map_v2/                         # new global pipeline/ego/validation tests
```

### Structure Rationale

- **`services/map_v2/`:** Isolates risky algorithm and schema-transition logic without destabilizing shipped v1 modules.
- **`routes/map.py` as compatibility shell:** Preserves frontend behavior while backend internals switch under the same contract.
- **`persistence.py` RPC-only boundary:** Enforces milestone rule that runtime `profiles` access stays on secured RPC paths.

## Architectural Patterns

### Pattern 1: Strangler Facade for Backend Compatibility

**What:** Keep route signatures and payload shape fixed, but route implementation through a new internal facade.
**When to use:** Frontend is frozen and backend semantics must change deeply.
**Trade-offs:** Slight temporary duplication, but much lower rollout risk.

**Example:**
```python
# backend/routes/map.py
@router.get("/{user_id}")
async def get_map(user_id: str, acting_user_id: str = Depends(get_current_user)):
    return map_v2_facade.get_compat_map(viewer_id=user_id, acting_user_id=acting_user_id)
```

### Pattern 2: Batch-Compute + Request-Time Projection Split

**What:** Daily global coordinate compute writes one row per user; request path only filters and translates.
**When to use:** Heavy compute is global and read traffic is frequent.
**Trade-offs:** Requires strict version metadata handling (`version_date`, `computed_at`).

**Example:**
```python
# pseudo-flow
global_coords = run_global_pipeline()      # once/day
persist(global_coords, version_date=today)

ego_nodes = get_mutual_friend_nodes(viewer_id)
return translate_to_origin(ego_nodes, viewer_id)
```

### Pattern 3: Fail-Closed Validation Gates

**What:** Gate data, algorithm, persistence, and API contract before exposing new coordinates.
**When to use:** Migration changes both schema semantics and algorithm behavior.
**Trade-offs:** More code paths, but prevents silent corruption and rollback pain.

## Data Flow

### Global Batch Flow (new)

```
Scheduler daily UTC trigger
    ↓
global_pipeline.fetch_inputs()
    ↓
feature_builder (profiles -> vectors)
    ↓
umap_projector (Stage A global prior)
    ↓
interaction_refiner (Stage B sparse graph force)
    ↓
validation_gate_service.pre_write_checks()
    ↓
persistence.upsert_global_coordinates()
    ↓
validation_gate_service.post_write_checks()
```

### Ego Request Flow (new read path)

```
GET /map/{user_id}
    ↓
map_v2_facade.get_compat_map()
    ↓
ego_query.resolve_mutual_friends(profiles.friends)
    ↓
ego_query.fetch_global_coords(viewer + friends)
    ↓
ego_query.translate_to_viewer_origin()
    ↓
suggestions fallback (optional, bounded)
    ↓
compat response mapper (existing JSON shape + metadata)
```

### Key Data Flow Changes

1. **Storage model:** `map_coordinates` changes from per-center/per-other history to one row per user global coordinates.
2. **Compute model:** one global daily run replaces per-user repeated recomputation.
3. **Read model:** per-request ego translation and mutual-friend filtering replaces precomputed personalized rows.
4. **Delivery model:** 7pm local jobs become cache warm only, never coordinate recomputation.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| Supabase Postgres | RPC-backed read/write adapters | Keep `profiles` runtime reads on secured RPC functions; avoid direct table reads in algorithm runtime paths |
| APScheduler (3.x) | In-process `AsyncIOScheduler` + `CronTrigger` | Configure `max_instances=1`, `coalesce=True`, `misfire_grace_time` on global job for restart safety |
| UMAP (`umap-learn`) | In-process embedding stage | Use vector input directly; avoid dense precomputed NxN distance matrix |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| `routes/map.py` <-> `services/map_v2/facade.py` | Direct function call | Route stays thin; all new branching lives in facade |
| `facade.py` <-> `global_pipeline.py` | Direct call (trigger path) | Trigger endpoint should invoke controlled global run path, not legacy per-user recompute |
| `facade.py` <-> `ego_query.py` | Direct call (read path) | Keeps query-time translation isolated and testable |
| `global_pipeline.py` <-> `persistence.py` | Typed payload boundary | Enforce one-row-per-user payload contract before DB write |
| `global_pipeline.py` <-> `validators.py` | Gate contract (`raise` on fail) | Fail closed before writes and before publishing version metadata |
| `scheduler.py` <-> `global_pipeline.py` | Scheduled invocation | Daily UTC compute + optional per-timezone cache warm |

## Validation Gate Architecture

### Gate A: Input/Data Integrity (pre-compute)

**Checks:** minimum user count, profile field completeness thresholds, canonical interaction pairs, no orphan IDs.
**Fail action:** abort run, keep previous `version_date` live.

### Gate B: Algorithm Stability (pre-write)

**Checks:** finite coordinates, centroid/radius sanity, per-user movement clamp against `prev_x/prev_y`, collapse detection.
**Fail action:** abort write, emit run diagnostics.

### Gate C: Persistence Correctness (post-write)

**Checks:** row count approximately active user count, uniqueness on `user_id`, metadata uniformity for `version_date`.
**Fail action:** mark run invalid; do not advertise new version to read path.

### Gate D: API Contract Compatibility (pre-response)

**Checks:** viewer at `(0,0)`, only mutual friends returned (plus marked suggestions), required response keys preserved.
**Fail action:** return explicit 5xx/422 with actionable logs (never silent partial shape drift).

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 0-1k users | Single-process FastAPI + APScheduler is acceptable; run daily global compute inline |
| 1k-100k users | Keep sparse interaction graph, tighten refinement iterations, add cache warm only for heavy timezones |
| 100k+ users | Move global compute to dedicated worker/service, keep API process read-only for ego queries |

### Scaling Priorities

1. **First bottleneck:** global compute runtime; solve with sparse graph limits and isolated worker execution.
2. **Second bottleneck:** ego query fan-out for high-degree users; solve with bounded friend/suggestion query caps and indexes.

## Anti-Patterns

### Anti-Pattern 1: Recomputing Full Map per User Request

**What people do:** Call heavy pipeline from user-triggered map reads.
**Why it's wrong:** Reintroduces O(N) or worse per-request cost and scheduler duplication risk.
**Do this instead:** Compute globally once/day and keep request path as lightweight extraction + translation.

### Anti-Pattern 2: Dense NxN Distance Construction in V2

**What people do:** Build full pairwise profile distance matrix before projection.
**Why it's wrong:** O(N^2) memory/cost undermines milestone scalability goal.
**Do this instead:** Embed direct feature vectors (UMAP Stage A) and refine with sparse interaction edges only.

### Anti-Pattern 3: Shipping Coordinates Without Validation Gates

**What people do:** Persist and serve every run regardless of quality checks.
**Why it's wrong:** One bad run can corrupt UX and force emergency rollback.
**Do this instead:** Keep prior version active unless all gates pass.

## Recommended Build Order (dependency-safe)

1. **Introduce v2 persistence contract (shadow-first).**
   - Add new RPCs and schema semantics for one-row-per-user `map_coordinates` in an idempotent migration.
   - Keep legacy RPCs callable until route cutover; do not break current `/map` contract yet.

2. **Add `services/map_v2/` skeleton with validators and facade.**
   - Wire no-op facade into `routes/map.py` behind a feature flag.
   - Goal: integration plumbing lands before algorithm risk.

3. **Implement Stage A global embedding (profile vectors -> UMAP).**
   - Reuse existing `UserProfile` field semantics and matching weights where possible.
   - Persist to shadow version metadata only after Gate A/B/C pass.

4. **Implement Stage B sparse interaction refinement with movement clamp.**
   - Add recency-aware edge weighting from `interactions.last_updated`.
   - Validate drift against `prev_x/prev_y` before activation.

5. **Implement ego-map query path + suggestions fallback.**
   - Mutual-friend filter from `profiles.friends` (mutual-only rule).
   - Translate to viewer origin and preserve existing response shape.

6. **Switch scheduler to global-daily compute and optional 7pm cache warm.**
   - Ensure 7pm jobs do delivery/cache only.
   - Add APScheduler safeguards (`replace_existing`, `max_instances=1`, misfire handling).

7. **Cut over compatibility route to v2 facade, then retire legacy per-user pipeline path.**
   - Keep endpoint path stable; remove dead code only after contract tests and parity checks pass.

## Sources

- Local architecture and milestone constraints:
  - `.planning/milestones/v2-NOTES.md` (HIGH)
  - `.planning/codebase/ARCHITECTURE.md` (HIGH)
  - `.planning/codebase/STRUCTURE.md` (HIGH)
  - `backend/routes/map.py`, `backend/services/map_pipeline/*.py`, `backend/app.py` (HIGH)
- FastAPI lifespan guidance (Context7, FastAPI docs/release notes):
  - https://github.com/fastapi/fastapi/blob/master/docs/en/docs/advanced/events.md (HIGH)
  - https://github.com/fastapi/fastapi/blob/master/docs/en/docs/release-notes.md (HIGH)
- APScheduler 3.x operational behavior (official docs):
  - https://apscheduler.readthedocs.io/en/3.x/userguide.html (HIGH)
- UMAP vector-input and sparse support (Context7 over official UMAP docs):
  - https://umap-learn.readthedocs.io/en/latest/sparse (HIGH)
  - https://umap-learn.readthedocs.io/en/latest/transform.html (HIGH)
- Supabase RPC and function security patterns:
  - https://supabase.com/docs/reference/javascript/rpc (HIGH)
  - https://supabase.com/docs/guides/database/functions (HIGH)
  - https://supabase.com/docs/guides/database/postgres/row-level-security (HIGH)

---
*Architecture research for: SixDegrees v2.0 global coordinate map engine milestone*
*Researched: 2026-02-26*
