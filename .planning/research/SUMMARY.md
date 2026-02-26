# Project Research Summary

**Project:** SixDegrees v2.0 Global Coordinate Map Engine
**Domain:** Backend-only social-graph map platform migration (FastAPI + Supabase)
**Researched:** 2026-02-26
**Confidence:** MEDIUM-HIGH

## Executive Summary

This project is a backend architecture migration for a social "People Map" product: move from demo-era, per-viewer map computation/storage to a production global coordinate engine with request-time ego extraction. Expert implementations in this space separate heavy batch compute (global embeddings) from lightweight read serving (viewer-centered translation), keep one coordinate row per user, and enforce strict compatibility at the API boundary so frontend behavior does not change.

The recommended approach is a strangler migration: keep `backend/routes/map.py` contract stable, introduce a new `services/map_v2/` facade and pipeline, and cut over in phases behind validation gates. Core technical direction is UMAP vector embedding + sparse interaction refinement (no dense NxN matrices), RPC-bound persistence in Supabase, APScheduler daily global runs, and fail-closed validation before publish (`version_date` + `computed_at` metadata as first-class release signals).

The key risks are semantic data-migration drift, privacy/security regressions in map reads/suggestions, and operational instability from scheduler duplication or algorithm jitter. Mitigation is clear and non-optional: atomic map semantics reset, canonical mutual-friend/authZ enforcement, SECURITY DEFINER hardening, single-scheduler runtime guarantees, and movement stability thresholds that block bad versions from being published.

## Key Findings

### Recommended Stack

Research strongly supports an in-process Python stack that preserves current backend deployment shape while removing known v1 scaling bottlenecks. The highest-leverage decision is replacing precomputed-distance t-SNE flow with vector-input UMAP plus sparse graph refinement, then instrumenting pipeline quality and runtime SLOs.

**Core technologies:**
- `umap-learn==0.5.11`: Stage A manifold embedding from profile vectors - avoids dense NxN memory blowups and aligns with v2 sparse-scale goals.
- `scipy==1.17.1`: sparse adjacency and numeric kernels - enables efficient Stage B interaction refinement with `E << N^2`.
- `scikit-learn==1.8.0`: preprocessing and fallback manifold utilities - reuses existing dependency surface and lowers migration risk.
- `APScheduler==3.11.2`: daily UTC compute + timezone-local delivery jobs - compatible with current FastAPI lifespan scheduler model.

Critical version/pattern requirements: pin `pynndescent==0.6.0` with UMAP for deterministic behavior; keep single-worker scheduler topology; explicitly avoid full NxN pairwise distance materialization in production.

### Expected Features

The milestone is centered on correctness and scalability features, not UI expansion. Must-haves are strongly tied to existing locked constraints: one-row global coordinates, request-time viewer-centered map extraction, safe sparse fallback suggestions, and validation-gated publish flow.

**Must have (table stakes):**
- Global one-row-per-user coordinate source of truth with daily batch publish.
- Ego map extraction with viewer fixed at `(0,0)` and strict mutual-friend filtering.
- Sparse/empty-map fallback suggestions with bounded top-N and explicit `is_suggestion` flag.
- Stable backward-compatible API contract with machine-readable failures and run metadata.
- Authorization guards that prevent cross-user map access.

**Should have (competitive):**
- Movement continuity policy (anti-jitter clamp + stability metrics).
- Two-stage embedding (profile manifold + sparse interaction refinement).
- Versioned validation gate before publish to block bad runs.
- 7pm local pre-warm delivery path that never recomputes embeddings.

**Defer (v2+):**
- Suggestion explanation factors and adaptive diversification.
- Near-real-time incremental recompute and push/notification updates.

### Architecture Approach

The architecture recommendation is a compatibility-preserving strangler: route handlers stay stable while internals move to `services/map_v2/` modules (`facade`, `global_pipeline`, `feature_builder`, `umap_projector`, `interaction_refiner`, `ego_query`, `validators`, `persistence`). Data flow is explicitly split into (1) scheduled global compute and gated publish, then (2) request-time ego filtering/translation plus optional suggestions. The critical design pattern across research is fail-closed behavior at every boundary: if data, stability, persistence, or contract checks fail, keep prior version live.

**Major components:**
1. `map_v2/global_pipeline.py` - orchestrates fetch -> embed -> refine -> validate -> persist global coordinates.
2. `map_v2/ego_query.py` - resolves mutual friends, fetches global rows, translates to viewer origin, applies bounded suggestions.
3. `map_v2/validators.py` - enforces Gate A-D checks (input integrity, algorithm stability, persistence correctness, API compatibility).
4. `services/map_pipeline/scheduler.py` - runs daily global compute and delivery-only timezone warm jobs with singleton safeguards.

### Critical Pitfalls

1. **Mixed `map_coordinates` semantics during cutover** - treat migration as a semantic reset and atomically switch RPC/contracts to one-row-per-user.
2. **O(N^2) regression from dense distance matrices** - prohibit full pairwise matrices in production; use vector UMAP + sparse refinement only.
3. **Security/privacy drift on map reads** - enforce self-access (or explicit policy), canonical mutuality checks, and suggestion payload allowlisting.
4. **Coordinate jitter and trust collapse** - enforce per-run movement clamps and fail publish if drift thresholds are exceeded.
5. **Scheduler duplication/misfires** - preserve single-worker scheduler topology with stable job IDs, coalescing, and restart-safe settings.

## Implications for Roadmap

Based on combined research, suggested phase structure:

### Phase 1: Data Contract and Safety Baseline
**Rationale:** Migration safety is the hard dependency for all downstream algorithm and API work.
**Delivers:** One-row-per-user `map_coordinates` semantics, hardened RPC boundary, legacy dependency inventory/cleanup plan.
**Addresses:** Global coordinate source-of-truth feature and validation-gate prerequisite.
**Avoids:** Mixed-semantics cutover failures, hidden `user_profiles` runtime dependency, SECURITY DEFINER hardening gaps.

### Phase 2: Global Compute Engine (Stage A/B + Publish Gates)
**Rationale:** Global compute must exist and be stable before request-time ego serving can be trusted.
**Delivers:** UMAP embedding, sparse interaction refinement, movement continuity controls, Gate A/B/C publish checks, versioned writes.
**Uses:** `umap-learn`, `scipy.sparse`, pinned `pynndescent`, APScheduler orchestration hooks.
**Implements:** `map_v2/global_pipeline.py`, `feature_builder.py`, `umap_projector.py`, `interaction_refiner.py`, `validators.py`.

### Phase 3: Ego API Compatibility and Safe Suggestions
**Rationale:** User-visible behavior depends on accurate read-path translation on top of trusted global coordinates.
**Delivers:** Mutual-friend filtering, viewer-origin translation, bounded fallback suggestions, contract-compatible payload mapping, authZ enforcement.
**Addresses:** P1 ego extraction and empty-map resilience features without frontend changes.
**Avoids:** Mutuality drift, origin translation bugs, suggestion data leaks, cross-user map access.

### Phase 4: Scheduler Operations, Warm Delivery, and Cutover
**Rationale:** Operational correctness determines reliability after functional readiness.
**Delivers:** Daily global schedule, delivery-only 7pm local warm jobs, run observability, duplicate-job protection, v1 path retirement.
**Addresses:** P2 pre-warm behavior and production SLO readiness.
**Avoids:** Scheduler duplication/misfire storms and hidden recompute in delivery jobs.

### Phase Ordering Rationale

- Data semantics and security hardening come first because every later phase assumes trustworthy persistence and access boundaries.
- Compute quality gates precede API cutover so frontend-facing endpoints never serve unstable or invalid coordinate versions.
- Ego extraction and suggestions are grouped because they share mutuality, authZ, payload-contract, and privacy controls.
- Scheduler/warm/cutover is last to reduce blast radius: operational rollout after algorithm + contract correctness is proven.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 2:** Embedding/refinement parameter tuning and benchmark thresholds at expected production user counts.
- **Phase 3:** Suggestion ranking policy (distance/diversity/recency) and abuse-resistant limits under real traffic patterns.
- **Phase 4:** If growth trend approaches 100k+ users, evaluate dedicated worker/service split for global compute.

Phases with standard patterns (can usually skip dedicated research-phase):
- **Phase 1:** SQL migration hygiene, RPC hardening, and compatibility-schema rollout patterns are well documented.
- **Phase 4 (current scale):** APScheduler singleton configuration + cache-warm scheduling is established and low novelty if single-worker remains.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Strong alignment across official docs and current codebase constraints; concrete pinned versions and integration points are specified. |
| Features | MEDIUM | Core P1 set is clear, but differentiator ranking and suggestion behavior still need product-policy calibration. |
| Architecture | HIGH | Recommended module boundaries, flows, and migration pattern are detailed and dependency-ordered. |
| Pitfalls | HIGH | Risks are concrete, phase-mapped, and include acceptance checks and recovery strategies. |

**Overall confidence:** MEDIUM-HIGH

### Gaps to Address

- **Parameter calibration gap:** Final UMAP/refinement hyperparameters and movement thresholds require benchmark-backed tuning on representative data before locking SLA.
- **Suggestion policy gap:** Exact ranking signals and payload explainability should be validated with privacy and UX acceptance criteria during Phase 3 planning.
- **Scale-transition gap:** Trigger conditions for moving compute off API process (worker split) need explicit operational thresholds in roadmap exit criteria.

## Sources

### Primary (HIGH confidence)
- `.planning/research/STACK.md` - stack recommendations, version pins, integration points.
- `.planning/research/FEATURES.md` - table stakes/differentiators/anti-features and dependency mapping.
- `.planning/research/ARCHITECTURE.md` - target module boundaries, data flows, build order.
- `.planning/research/PITFALLS.md` - critical risk register, acceptance checks, recovery guidance.
- Official documentation referenced in research: UMAP, SciPy sparse, scikit-learn TSNE/NN, APScheduler, FastAPI, Supabase RPC/RLS, PostgreSQL `CREATE FUNCTION` security guidance.

### Secondary (MEDIUM confidence)
- Context7-indexed framework/library docs used in research synthesis (FastAPI, UMAP, scikit-learn, Prometheus instrumentator).
- PyPI metadata snapshots used for version baseline validation.

### Tertiary (LOW confidence)
- Comparative algorithm references (e.g., Neo4j GDS similarity patterns) used as directional benchmarking context, not direct implementation dependency.

---
*Research completed: 2026-02-26*
*Ready for roadmap: yes*
