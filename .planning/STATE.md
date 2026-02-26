---
gsd_state_version: 1.0
milestone: v2.0
milestone_name: milestone
status: in_progress
last_updated: "2026-02-26T22:57:18.371Z"
progress:
  total_phases: 1
  completed_phases: 0
  total_plans: 3
  completed_plans: 2
---

# Project State

## Project Reference

See: `.planning/PROJECT.md` (updated 2026-02-26)

**Core value:** A user opens the People Map and immediately sees meaningful nearby people around themselves at (0,0), with stable, explainable positions that update daily.
**Current focus:** Phase 20 - Global Coordinate Data Contract

## Current Position

Phase: 1 of 4 (Phase 20 - Global Coordinate Data Contract)
Plan: 3 of 3 in current phase
Status: In progress
Last activity: 2026-02-26 - Completed 20-02 interactions rebuild and FK repoint execution.

Progress: [███████░░░] 67%

## Performance Metrics

**Velocity:**
- Total plans completed: 2
- Average duration: 3 min
- Total execution time: 0.1 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 20 | 2 | 6 min | 3 min |

**Recent Trend:**
- Last 5 plans: 20-02 (2 min), 20-01 (4 min)
- Trend: Stable
| Phase 20 P02 | 2 min | 2 tasks | 2 files |

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

### Pending Todos

None yet.

### Blockers/Concerns

- Parameter tuning and stability thresholds for global embedding require benchmark-based calibration during phase planning.
- Live DB currently has interactions FKs to `user_profiles`; Phase 20 must resolve FK repoint + integrity validation before any drop.

## Session Continuity

Last session: 2026-02-26 17:57 EST
Stopped at: Completed 20-02-PLAN.md
Resume file: None
