---
gsd_state_version: 1.0
milestone: v2.0
milestone_name: milestone
status: in_progress
last_updated: "2026-02-27T05:21:05.667Z"
progress:
  total_phases: 6
  completed_phases: 5
  total_plans: 17
  completed_plans: 15
---

# Project State

## Project Reference

See: `.planning/PROJECT.md` (updated 2026-02-26)

**Core value:** A user opens the People Map and immediately sees meaningful nearby people around themselves at (0,0), with stable, explainable positions that update daily.
**Current focus:** Phase 25 - Interaction Sensitivity and Dynamic Distance Tuning

## Current Position

Phase: 6 of 6 (Phase 25 - Interaction Sensitivity and Dynamic Distance Tuning)
Plan: 1 of 3 in current phase
Status: In Progress
Last activity: 2026-02-27 - Completed 25-01 interaction sensitivity scaling and dynamic tuning regressions.

Progress: [█████████░] 88%

## Performance Metrics

**Velocity:**
- Total plans completed: 5
- Average duration: 3 min
- Total execution time: 0.2 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 20 | 3 | 8 min | 3 min |

**Recent Trend:**
- Last 5 plans: 21-02 (5 min), 21-01 (5 min), 20-03 (2 min), 20-02 (2 min), 20-01 (4 min)
- Trend: Stable
| Phase 20 P02 | 2 min | 2 tasks | 2 files |
| Phase 20 P03 | 2 min | 2 tasks | 3 files |
| Phase 21 P01 | 5min | 3 tasks | 8 files |
| Phase 21 P02 | 5min | 3 tasks | 9 files |
| Phase 22 P01 | 1min | 2 tasks | 2 files |
| Phase 22 P02 | 2min | 3 tasks | 3 files |
| Phase 22 P03 | 1min | 2 tasks | 3 files |
| Phase 23-scheduler-operations-and-safe-rollout P01 | 4min | 2 tasks | 3 files |
| Phase 23 P02 | 4min | 2 tasks | 6 files |
| Phase 23-scheduler-operations-and-safe-rollout P03 | 3min | 2 tasks | 3 files |
| Phase 24 P01 | 4min | 2 tasks | 4 files |
| Phase 24 P02 | 5min | 2 tasks | 6 files |
| Phase 24 P03 | 2min | 2 tasks | 4 files |
| Phase 25 P01 | 2min | 2 tasks | 6 files |

## Accumulated Context

### Decisions

Decisions are logged in `.planning/PROJECT.md` Key Decisions table.
Recent decisions affecting current work:

- [Phase 20-23]: v2.0 phases start at 20 and derive only from v2.0 requirements.
- [Phase 22]: frontend behavior remains compatible with no frontend code changes.
- [Phase 20/22]: `profiles` and `pending_requests` schema remain unchanged.
- [Phase 20]: Do not migrate legacy `user_profiles` users into `profiles`; v2.0 runtime scope is existing `profiles` users only.
- [Phase 20]: Rebuild `interactions` from `posts`/`likes`/`comments` for profiles users, then repoint FKs to `profiles(id)`.
- [Phase 23]: Milestone cannot close until DB/runtime have zero `user_profiles` dependency and safe drop is complete.
- [Phase 20]: Use upsert_global_map_coordinates JSONB RPC so backend publishes one batch timestamp/version across all users.
- [Phase 20]: Preserve one-step movement continuity in SQL by assigning prev_x/prev_y from current row on conflict updates.
- [Phase 20]: Rebuild interactions via truncate and deterministic re-aggregation from profile-scoped activity before enforcing FK constraints.
- [Phase 20]: Standardize interaction FK names to fk_interactions_user_a_profiles and fk_interactions_user_b_profiles after removing any user_profiles references.
- [Phase 20]: Map route reads now use get_global_map_coordinates and return shared version metadata from global rows.
- [Phase 20]: Map contract tests now require version_date/computed_at with deterministic RPC mocks to prevent false-green 404 behavior.
- [Phase 21]: Use sparse profile vectors plus k-NN graph extraction to avoid dense NxN precompute in the pipeline path.
- [Phase 21]: Apply interaction refinement as iterative sparse edge pulls with exponential recency decay from optional days-since fields.
- [Phase 21]: Expose optional prior anchors in run_pipeline and enforce per-user movement clipping through a dedicated stability stage.
- [Phase 21]: Use a two-step validation model: pre-publish input/embedding gates and post-publish persistence coherence checks.
- [Phase 21]: Persist diagnostics through a secured service-role RPC so map serving stays read-compatible while compute runs remain auditable.
- [Phase 21]: Keep map response contract unchanged by confining publish gating to pipeline orchestration and tests.
- [Phase 22]: Expose only id, nickname, and friends in get_ego_map_profiles for serving-safe projection.
- [Phase 22]: Keep build_ego_map pure and deterministic with no Supabase I/O.
- [Phase 22]: Select fallback suggestions by translated-distance then user_id for stable ordering.
- [Phase 22]: Enforce self-only GET /map access and keep response shape backward-compatible with additive is_suggestion metadata.
- [Phase 23]: Use dedicated Supabase RPC lock key with owner token and TTL for global scheduler dedupe.
- [Phase 23]: Schedule one 00:00 UTC global recompute job and keep 19:00 timezone jobs warm-only.
- [Phase 23]: Store warmed map payloads per user with version_date/computed_at metadata for stale checks.
- [Phase 23]: Use latest diagnostics publish status plus get_last_good_version to choose fallback warm metadata.
- [Phase 23]: Guard legacy drop with trigger/counter prerequisite checks so migration fails closed before destructive DDL.
- [Phase 23]: Validate dependency detach at catalog level (FK/view/function) before dropping public.user_profiles.
- [Phase 24]: Use dedicated demo_* tables and helper RPCs so notebook iteration cannot touch production map tables.
- [Phase 24]: Generate deterministic user IDs/data with uuid5 and fixed fixtures so reruns are byte-stable.
- [Phase 24]: Run baseline and amplified scenarios through the same run_pipeline path with Eleanor as requesting anchor for direct before/after comparison.
- [Phase 24]: Emit notebook artifacts as stable CSV/JSON files under demo/data so Phase 24 notebook cells can load data without reshaping.
- [Phase 24]: Load notebook visuals from deterministic demo/data artifacts for rerunnable analysis.
- [Phase 24]: Use notebook JSON content-contract tests instead of kernel execution for fast deterministic CI checks.
- [Phase 25]: Use bounded exponential interaction sensitivity with tunable scale/exponent/normalizer/max cap to avoid early saturation while preserving safety bounds.
- [Phase 25]: Expose optional InteractionSensitivity overrides in run_pipeline for deterministic tuning sweeps without mutating global defaults.

### Pending Todos

None yet.

### Blockers/Concerns

- Parameter tuning and stability thresholds for global embedding require benchmark-based calibration during phase planning.
- Live DB currently has interactions FKs to `user_profiles`; Phase 20 must resolve FK repoint + integrity validation before any drop.

## Session Continuity

Last session: 2026-02-27T05:20:24Z
Stopped at: Completed 25-01-PLAN.md
Resume file: None
