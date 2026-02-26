# Feature Research

**Domain:** Production social-graph map backend (global coordinates + ego extraction)
**Researched:** 2026-02-26
**Confidence:** MEDIUM-HIGH

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing these = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Global O(N) coordinate source of truth | Social maps must load quickly at scale; per-viewer map materialization is not operationally viable | HIGH | One coordinate row per user, daily batch recompute, bounded movement using `prev_x/prev_y`; aligns with v2 locked intent and avoids O(N^2) storage/compute. |
| Request-time ego extraction with viewer at exact origin | Users expect "my map" centered on themselves, not a global canvas they must mentally translate | MEDIUM | Fetch viewer + mutual friends, translate to `(0,0)` origin; strict mutuality check from `profiles.friends`; no frontend change required. |
| Sparse/empty-map fallback suggestions | Empty maps feel broken; production social systems provide nearest alternatives when direct neighborhood is thin | MEDIUM | Return bounded top-N non-friend nearest neighbors with `is_suggestion=true`; cap N, exclude blocked/invalid/self rows, preserve backward-compatible payload shape. |
| Stable API contract with machine-readable validation failures | Clients need deterministic behavior across deploys; map failures must be debuggable without UI rewrites | MEDIUM | Keep existing route compatibility, add explicit problem types/status codes (422/409/503 patterns), include `version_date` and `computed_at` in success payload. |
| Safety and authorization guards on map reads | Social graph APIs must not leak other users' map states through permissive endpoints | MEDIUM | Enforce acting-user scope for self map route (or explicit authorized relationship policy), preserve JWT checks, fail closed on auth ambiguity. |

### Differentiators (Competitive Advantage)

Features that set the product apart. Not required, but valuable.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Movement continuity policy (anti-jitter map) | Users trust the map when day-over-day movement is explainable, not chaotic | HIGH | Add max-step clamp and stability metrics per run; reject writes when drift exceeds threshold; expose movement metadata for observability. |
| Two-stage embedding (profile manifold + sparse interaction refinement) | Better semantic quality than profile-only maps while avoiding dense pairwise costs | HIGH | UMAP over profile vectors + sparse interaction-force refinement; explicitly avoid full NxN distance matrix. |
| Quality-scored suggestions (distance + diversity + recency) | Fallback suggestions feel intentional rather than random filler | MEDIUM-HIGH | Rank nearest candidates with guardrails (distance banding, optional recency signal), return explanation hints for auditing. |
| Versioned validation gate before publish | Reduces bad map rollouts and expensive rollback events | HIGH | Compute into candidate snapshot, run data/algorithm/API contract checks, then atomically publish version_date if checks pass. |
| 7pm local pre-warm delivery path (no recompute) | Faster perceived freshness at predictable local time without compute amplification | MEDIUM | Warm cache by timezone using latest global version; jobs must be delivery-only and never trigger full embedding recompute. |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but create problems.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Per-viewer persisted map rows | "Personalized map per user sounds straightforward" | O(N^2) storage, N full recomputes/day, operationally non-scalable | Keep one global coordinate per user and do request-time ego translation. |
| Full NxN pairwise similarity matrix in production pipeline | "Seems mathematically complete" | Memory/compute blow-up as user count grows; blocks daily SLA | Use sparse graph methods and local neighbor operations only. |
| Realtime recompute on every profile/interaction write | "Always freshest map" | Queue storms, unstable coordinates, poor UX from jitter | Daily global recompute + optional lightweight warm cache refresh. |
| Unbounded suggestions with weak filtering | "More suggestions = better" | Noisy UX, policy risk, larger payloads, slower responses | Hard-cap top-N, enforce policy filters, include confidence/flags. |
| Frontend-dependent rollout requirements | "Let's redesign map payload/UI together" | Violates milestone scope and delays backend correctness | Maintain backward-compatible API; add optional fields only. |

## Feature Dependencies

```
[Global coordinate source of truth]
    └──requires──> [Two-stage embedding + sparse refinement]
                         └──requires──> [Daily scheduler + publish pipeline]

[Request-time ego extraction]
    └──requires──> [Mutual-friend resolver + auth guard]

[Fallback suggestions]
    └──requires──> [Nearest-neighbor candidate index/query]
    └──requires──> [Policy filters + bounded top-N]

[Versioned validation gate]
    └──requires──> [Data quality checks]
    └──requires──> [Algorithm stability checks]
    └──requires──> [API contract checks]

[7pm pre-warm cache]
    └──requires──> [Published global version]
    └──conflicts──> [Realtime recompute on delivery job]
```

### Dependency Notes

- **Global coordinate source of truth requires two-stage embedding:** one-row-per-user is only useful if compute quality and scalability hold under sparse graph constraints.
- **Ego extraction requires strict auth + mutuality resolver:** correctness is both product quality and security posture; asymmetric friend arrays must fail into non-visibility.
- **Fallback suggestions require candidate retrieval + policy filtering:** nearest candidates without policy guardrails create privacy and relevance failures.
- **Validation gate requires tri-layer checks:** data integrity alone is insufficient; stability and contract checks must pass before publishing a new version.
- **7pm pre-warm conflicts with recompute:** delivery jobs must consume existing version output only, or they reintroduce compute blow-up.

## MVP Definition

### Launch With (v2.0 milestone)

- [x] Global coordinate model with one row per user and daily batch publish - core scalability requirement.
- [x] Ego extraction API (mutual friends + origin translation + metadata) - core user-visible behavior.
- [x] Empty/sparse fallback suggestions (bounded top-N, `is_suggestion`) - prevents "blank map" failure mode.
- [x] Validation gates for data quality, movement stability, and API shape before publish - rollout safety requirement.

### Add After Validation (v2.x)

- [ ] Suggestion explanation payloads (rank factors, distance buckets) - add after baseline relevance metrics are stable.
- [ ] Adaptive top-N by graph density/timezone - add once request and cache hit metrics are available.

### Future Consideration (post-v2)

- [ ] Near-real-time incremental refinement between daily global runs - defer until queueing/worker architecture is introduced.
- [ ] Notification/push map update channel - intentionally deferred by milestone scope.

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Global one-row-per-user coordinates + daily publish | HIGH | HIGH | P1 |
| Ego extraction with strict mutual filtering and origin translation | HIGH | MEDIUM | P1 |
| Fallback suggestions (bounded, filtered, flagged) | HIGH | MEDIUM | P1 |
| Validation/publish gate (data + stability + contract checks) | HIGH | HIGH | P1 |
| 7pm local pre-warm (delivery-only) | MEDIUM | MEDIUM | P2 |
| Suggestion explainability metadata | MEDIUM | MEDIUM | P2 |
| Adaptive suggestion diversification | MEDIUM | HIGH | P3 |

**Priority key:**
- P1: Must have for milestone acceptance
- P2: Should have if milestone capacity permits
- P3: Nice to have, defer unless low-effort

## Competitor/Pattern Snapshot

| Pattern | Typical Production Behavior | Our v2.0 Approach |
|---------|-----------------------------|-------------------|
| Ego network rendering | Compute/serve a user-centered subgraph, not full-network payloads | Request-time ego extraction from global coordinates with origin translation |
| Sparse network fallback | Provide recommendation candidates when direct neighborhood is thin | Return bounded non-friend nearest suggestions with explicit suggestion flags |
| API error semantics | Use standard HTTP status + machine-readable error schema | Keep FastAPI response models + explicit error typing; align toward RFC 9457 problem details |
| Rollout safety | Publish only validated model snapshots | Versioned candidate run, gate checks, then atomic publish |

## Sources

- `.planning/PROJECT.md` (milestone constraints and locked scope) - HIGH
- `.planning/milestones/v2-NOTES.md` (accepted v2 model and phased intent) - HIGH
- `.planning/codebase/ARCHITECTURE.md` (current backend boundaries and scheduler shape) - HIGH
- `.planning/codebase/CONCERNS.md` (known map/security/performance failure modes) - HIGH
- FastAPI docs via Context7 (`/fastapi/fastapi`) - response models, additional responses, HTTPException patterns - HIGH
- UMAP docs via Context7 (`/websites/umap-learn_readthedocs_io_en`) - scalable manifold embedding and transform workflow - MEDIUM
- scikit-learn docs via Context7 (`/websites/scikit-learn_stable`) - nearest-neighbor query patterns for top-k/radius fallback - HIGH
- Neo4j GDS docs (`/algorithms/knn`, `/algorithms/node-similarity`) - sparse similarity/recommendation algorithm tradeoffs, complexity caveats - MEDIUM
- RFC 9457 (IETF, July 2023) - machine-readable HTTP problem detail standard - HIGH
- Supabase RLS docs (`/docs/guides/database/postgres/row-level-security`) - authorization/policy guardrails and performance practices - HIGH

---
*Feature research for: SixDegrees v2.0 global coordinate map backend*
*Researched: 2026-02-26*
