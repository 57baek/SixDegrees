# SixDegrees

## What This Is

SixDegrees is a social networking product centered on a People Map: a 2D view that places users near each other based on profile similarity and social interaction strength. The backend computes and serves map coordinates, and the frontend consumes map/profile APIs.

This repository currently has a FastAPI backend and a Vue 3 frontend. Milestone v2.0 focuses on replacing demo-era map scalability limits with a production-ready global coordinate model while keeping frontend compatibility.

## Core Value

A user opens the People Map and immediately sees meaningful nearby people around themselves at (0,0), with stable, explainable positions that update daily.

## Requirements

### Validated

- [x] Backend API + auth dependency pattern is established (`/profile`, `/interactions`, `/match`, `/map`)
- [x] Profiles are canonical in backend runtime model (`profiles` table + `UserProfile` model shape)
- [x] Interaction aggregation model exists (`interactions` canonical pair rows with counters)
- [x] Map pipeline + scheduler lifecycle exist and run from FastAPI lifespan
- [x] Backend test suite structure is stable (`pytest`, fixtures, deterministic mocks)

### Active

- [ ] Replace per-viewer map storage with one global coordinate row per user
- [ ] Rebuild map compute pipeline for sparse/scalable global embedding + interaction refinement
- [ ] Serve request-time ego maps using mutual friends from `profiles.friends` and origin translation
- [ ] Add robust algorithm/data/API validation so every run is auditable and safe to roll forward
- [ ] Keep compatibility for existing frontend behavior without frontend code changes

### Out of Scope

- Frontend code changes in `frontend/` - explicitly excluded for v2.0
- `profiles` schema changes - explicitly excluded for v2.0
- `pending_requests` table changes - explicitly excluded for v2.0
- New notification/push infrastructure - defer until after stable v2.0 map backend
- Unrelated product features (admin, moderation, OAuth, chat)

## Context

- Historical planning artifacts are archived in `.planning/archive/pre-v2-2026-02-25/`.
- Completed roadmap history lives under `.planning/milestones/v1.0-phases/` and `.planning/milestones/v1.1-phases/`.
- V2 architecture notes are in `.planning/milestones/v2-NOTES.md` and are treated as locked milestone intent.
- Current codebase map is in `.planning/codebase/`.
- The backend currently uses demo-era `map_coordinates` semantics that do not scale; v2.0 replaces that model.

## Constraints

- **Frontend scope:** No changes in `frontend/` - backend migration must be backward-compatible.
- **Schema lock:** No schema changes to `profiles` or `pending_requests`.
- **Security model:** Preserve authenticated route protections and current Supabase usage patterns.
- **Operational stability:** Keep single-worker scheduler constraints and avoid duplicated jobs.
- **Validation rigor:** Milestone requires strong algorithmic validation and migration safety checks.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Use `profiles.friends` mutuality for map visibility in v2.0 | Existing data source is available and frontend-safe without new follow system rollout | — Pending |
| Keep `profiles` schema unchanged | Frontend compatibility and explicit user constraint | — Pending |
| Repurpose `map_coordinates` to global per-user rows | Removes O(N^2) storage growth and per-view duplication | — Pending |
| Compute global map once daily, serve ego map at request time | Separates heavy batch compute from cheap read path | — Pending |
| Prioritize validation and rollout safety over new UI features | User requested algorithmic rigor and strong validations | — Pending |

## Current Milestone: v2.0 Global Coordinate Map Engine

**Goal:** Replace demo-era personalized map storage/computation with a scalable global coordinate architecture and validated ego-map serving path.

**Target features:**
- Global map compute pipeline (profile manifold + sparse interaction refinement)
- One-row-per-user coordinate storage with controlled movement continuity
- Request-time ego map extraction (viewer-centered, mutual-friend filtered)
- Strong validation gates (data quality, algorithm stability, API contract, migration correctness)

---
*Last updated: 2026-02-26 16:56:28 EST after starting milestone v2.0*
