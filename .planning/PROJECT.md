# SixDegrees

## What This Is

SixDegrees is a social networking platform built around a **People Map** — a personalized, daily-updated 2D interactive visualization that shows every user on the platform positioned relative to you in space. Closeness on the map reflects both profile similarity and interaction intensity. The defining insight is that the map is not egocentric: it also reflects relationships between other users relative to each other, surfacing invisible affinities that exist in the real world.

The platform runs on a Vue 3 + FastAPI + Supabase stack. The backend hosts a Python algorithm pipeline that computes map coordinates; the frontend renders the social experience.

## Core Value

The People Map: every user is always at (0, 0), and every other person on the platform is positioned by how close they are to you — combining who you are (profile similarity) and how you've interacted (engagement history).

## Requirements

### Validated

- ✓ Profile similarity computation (Jaccard for interests/languages, tiered for location/industry, binary for education, inverse-distance for age) — existing
- ✓ Weighted distance matrix from similarity scores (interests 35%, location 20%, languages 15%, field_of_study 10%, industry 10%, education 5%, age 5%) — existing
- ✓ Tiered KNN ranking (Tier 1: 5 nearest, Tier 2: next 10, Tier 3: within max_distance) — existing
- ✓ Supabase auth (frontend email/password login, session persisted in localStorage) — existing
- ✓ Vue 3 frontend shell (login, signup, home feed scaffold) — existing

### Active

- [ ] Replace PCA with t-SNE for 2D coordinate projection (preserves local neighborhood structure)
- [ ] Extend distance formula to include interaction data (likes + comments + DM counts, normalized, configurable α/β weights)
- [ ] Modular interaction scoring system (dict-driven interaction types, adding new type = 1 column + 1 weight)
- [ ] Origin translation: requesting user always at exactly (0, 0)
- [ ] Pull real user profile data from Supabase `user_profiles` table
- [ ] Pull interaction data from Supabase `interactions` table
- [ ] `map_coordinates` table with old + new coordinate rows for animation delta support
- [ ] `GET /map/{user_id}` API endpoint returning precomputed coordinates with tier + display_name
- [ ] Batch scheduler (APScheduler) running full pipeline at 7pm per-user-timezone daily
- [ ] Seed script: 10-15 mock users with varied profiles + seeded interactions in Supabase
- [ ] `test_map.py`: standalone matplotlib plot proving algorithm correctness (changing data changes plot)
- [ ] `people_map_demo.ipynb`: interactive Jupyter notebook with per-stage explanations and inline plots
- [ ] Backend JWT validation on all write endpoints (via `supabase.auth.get_user(token)`)
- [ ] `POST /interactions/like` — records like event, upserts `interactions.likes_count`
- [ ] `POST /interactions/comment` — records comment event, upserts `interactions.comments_count`
- [ ] `POST /interactions/dm` — records DM sent event, upserts `interactions.dm_count`
- [ ] `PUT /profile` — creates or updates authenticated user's profile in `user_profiles`
- [ ] DB schema spec + API contract doc for frontend team (read endpoint + all write endpoints)

### Out of Scope

- Full social feed UI (posts/likes/comments as visible features) — backend-only milestone
- Real-time map updates — architecture supports it, not building it
- Map animation — store old+new coords for future delta, don't build animation
- Redis / Celery — APScheduler or cron only
- Profile creation/editing UI — backend endpoint exists, no frontend UI
- Admin/moderation features — not this milestone
- DM messaging UI — backend records dm events, no messaging UI
- CORS production configuration — localhost only
- Deployment / Docker setup — local dev only
- Full production test suite — demo scripts only

## Context

**Existing algorithm pipeline** (`backend/services/matching/`): four modules cover similarity functions, weighted matrix construction, KNN clustering, and PCA projection. Logically sound; needs extension (add interaction data, swap PCA → t-SNE) and connection to real DB data.

**Current algorithmic gap**: no interaction data factored in at all. The algorithm runs on mock/hardcoded inputs, not real Supabase rows.

**Existing frontend**: Vue 3 shells for login, signup, home feed. Auth works via Supabase directly on the frontend. Home feed uses hardcoded mock data because `posts`/`likes`/`comments` tables don't exist.

**Known bugs in existing code**:
- `handleLogout()` in `Home.vue` is accidentally defined inside `loadPosts()` — scoping bug, logout crashes
- Backend has zero auth validation — any user_id is served
- CORS hardcoded to `localhost:5173`
- Several backend deps (SQLAlchemy, psycopg2, python-jose, passlib) unused

**This milestone is backend + algorithm only.** Frontend team will implement the People Map UI separately using the API contract this milestone produces.

## Constraints

- **Tech stack**: Python/FastAPI backend, Vue 3 frontend, Supabase (PostgreSQL + Auth) — no changes
- **Scheduler**: APScheduler or cron-compatible function only — no Redis, no Celery
- **Demo deliverable**: test_map.py + people_map_demo.ipynb connecting to real Supabase instance
- **Animation readiness**: `map_coordinates` table must store both old and new coordinate sets during transition window even though animation is not built
- **Interaction modularity**: adding new interaction type must require only 1 table column + 1 weight constant — no logic changes

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| t-SNE over PCA for 2D projection | PCA is linear and doesn't preserve local neighborhoods; t-SNE explicitly clusters similar users spatially — critical for People Map readability | — Pending |
| α/β configurable in config file | Allow tuning profile vs interaction weight without touching algorithm code | — Pending |
| Canonical pair ordering in interactions table (a < b) | Prevents duplicate rows for (A,B) vs (B,A); simplifies queries | — Pending |
| Batch precompute + store vs live compute | N×N t-SNE is expensive; precompute at 7pm and serve from DB eliminates per-request latency | — Pending |
| APScheduler over Celery/Redis | Simpler setup for this milestone; sufficient for daily batch job | — Pending |
| Dict-driven interaction type weights | Makes adding new interaction types a config change, not a code change | — Pending |
| Backend-mediated writes (no direct frontend → Supabase writes) | All interaction events and profile data go through FastAPI endpoints; frontend only calls Supabase directly for Auth. Enforces data integrity, centralizes validation, and ensures the algorithm always gets clean inputs | — Pending |

---
*Last updated: 2026-02-22 after architecture decision: backend-mediated writes*
