# SixDegrees

## What This Is

SixDegrees is a social networking platform built around a **People Map** — a personalized, daily-updated 2D interactive visualization that shows every user on the platform positioned relative to you in space. Closeness on the map reflects both profile similarity and interaction intensity. The defining insight is that the map is not egocentric: it also reflects relationships between other users relative to each other, surfacing invisible affinities that exist in the real world.

The platform runs on a Vue 3 + FastAPI + Supabase stack. The v1.0 backend delivers a complete algorithm pipeline: t-SNE projection on a combined profile + interaction distance matrix, precomputed daily per user timezone, and served via FastAPI. The frontend team consumes the API contract to build the People Map UI.

## Core Value

The People Map: every user is always at (0, 0), and every other person on the platform is positioned by how close they are to you — combining who you are (profile similarity) and how you've interacted (engagement history).

## Requirements

### Validated

- ✓ Profile similarity computation (Jaccard for interests/languages, tiered for location/industry, binary for education, inverse-distance for age) — existing
- ✓ Weighted distance matrix from similarity scores (interests 35%, location 20%, languages 15%, field_of_study 10%, industry 10%, education 5%, age 5%) — existing
- ✓ Tiered KNN ranking (Tier 1: 5 nearest, Tier 2: next 10, Tier 3: within max_distance) — existing
- ✓ Supabase auth (frontend email/password login, session persisted in localStorage) — existing
- ✓ Vue 3 frontend shell (login, signup, home feed scaffold) — existing
- ✓ Replace PCA with t-SNE for 2D coordinate projection — v1.0
- ✓ Extend distance formula to include interaction data (likes + comments + DM counts, normalized, configurable α/β weights) — v1.0
- ✓ Modular interaction scoring system (dict-driven interaction types, adding new type = 1 column + 1 weight) — v1.0
- ✓ Origin translation: requesting user always at exactly (0, 0) — v1.0
- ✓ Pull real user profile data from Supabase `user_profiles` table — v1.0
- ✓ Pull interaction data from Supabase `interactions` table — v1.0
- ✓ `map_coordinates` table with old + new coordinate rows for animation delta support — v1.0
- ✓ `GET /map/{user_id}` API endpoint returning precomputed coordinates with tier + display_name — v1.0
- ✓ `POST /map/trigger/{user_id}` manual pipeline trigger for testing/demo — v1.0
- ✓ Batch scheduler (APScheduler) running full pipeline at 7pm per-user-timezone daily — v1.0
- ✓ Seed script: 20 mock users with varied profiles + seeded interactions in Supabase — v1.0
- ✓ `test_map.py`: standalone matplotlib plot proving algorithm correctness — v1.0
- ✓ `people_map_demo.ipynb`: interactive Jupyter notebook with per-stage plots — v1.0
- ✓ Backend JWT validation on all write endpoints (via `supabase.auth.get_user(token)`) — v1.0
- ✓ `POST /interactions/like` — records like event, upserts `interactions.likes_count` — v1.0
- ✓ `POST /interactions/comment` — records comment event, upserts `interactions.comments_count` — v1.0
- ✓ `POST /interactions/dm` — records DM sent event, upserts `interactions.dm_count` — v1.0
- ✓ `PUT /profile` — creates or updates authenticated user's profile in `user_profiles` — v1.0
- ✓ DB schema spec + API contract doc for frontend team — v1.0

### Active

_(Next milestone — planning in progress)_

### Out of Scope

- Full social feed UI (posts/likes/comments as visible features) — backend-only through v1.0
- Real-time map updates — architecture supports it, not building it
- Map animation — store old+new coords for future delta, don't build animation
- Redis / Celery — APScheduler sufficient; added complexity not justified
- Profile creation/editing UI — backend endpoint exists, no frontend UI
- Admin/moderation features
- DM messaging UI — backend records dm events, no messaging UI
- CORS production configuration — localhost only
- Deployment / Docker setup — local dev only
- Full production test suite — demo scripts only
- openTSNE / multi-worker scheduler — v2 concerns

## Context

**Shipped v1.0:** Complete backend algorithm pipeline — ~3,863 LOC (Python/TS/Vue), 113 files changed, 22 days.

**Tech stack:** Python 3.14 / FastAPI / Supabase PostgreSQL + Auth / scikit-learn 1.8.0 / APScheduler 3.x / Vue 3

**Current codebase state:**
- `backend/services/map_pipeline/` — complete pipeline (interaction.py, scoring.py, tsne_projector.py, origin_translator.py, data_fetcher.py, coord_writer.py, scheduler.py)
- `backend/routes/` — map.py, interactions.py, profile.py, deps.py (auth), match.py (existing)
- `scripts/` — test_map.py, people_map_demo.ipynb
- `docs/` — API_CONTRACT.md, DB_SCHEMA.md
- `frontend/` — Vue 3 shell; home feed uses hardcoded mock data (posts/likes/comments tables don't exist)

**Known bugs / tech debt carried forward:**
- `handleLogout()` in `Home.vue` scoped inside `loadPosts()` — crashes on logout
- `routes/auth.py` dead-code stub (pre-existing, not registered in app.py)
- `POST /interactions/dm` response string `"dm recorded"` vs spec `"dms recorded"` (1-char fix)
- `DB_SCHEMA.md` documents wrong env var `SUPABASE_SERVICE_ROLE_KEY` (should be `SUPABASE_KEY`)
- Existing `/match` routes have no JWT validation (out of scope v1.0)
- `psycopg2-binary` fails to build on macOS arm64 + Python 3.14 (not blocking; supabase-py uses HTTP)

**Single-worker constraint:** `uvicorn app:app --reload` only — multi-worker causes APScheduler double-firing.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| t-SNE over PCA for 2D projection | PCA is linear and doesn't preserve local neighborhoods; t-SNE explicitly clusters similar users spatially — critical for People Map readability | ✓ Good — `metric='precomputed'` with `init='random'` works; `max_iter` not `n_iter` (sklearn 1.5 rename) |
| α/β configurable in config file | Allow tuning profile vs interaction weight without touching algorithm code | ✓ Good — α=0.6, β=0.4 in `config/algorithm.py`; zero magic numbers in algorithm code |
| Canonical pair ordering in interactions table (a < b) | Prevents duplicate rows for (A,B) vs (B,A); simplifies queries | ✓ Good — enforced in Python (min/max) before RPC call; DB CHECK is second defense |
| Batch precompute + store vs live compute | N×N t-SNE is expensive; precompute at 7pm and serve from DB eliminates per-request latency | ✓ Good — `map_coordinates` table with `is_current` flag; old rows retained for future animation delta |
| APScheduler over Celery/Redis | Simpler setup for this milestone; sufficient for daily batch job | ✓ Good — single-worker constraint documented; acceptable at current scale |
| Dict-driven interaction type weights | Makes adding new interaction types a config change, not a code change | ✓ Good — adding new type = 1 column + 1 `INTERACTION_WEIGHTS` entry; zero logic changes |
| Backend-mediated writes (no direct frontend → Supabase writes) | All interaction events and profile data go through FastAPI endpoints; frontend only calls Supabase directly for Auth. Enforces data integrity, centralizes validation | ✓ Good — JWT validation on all write endpoints via `supabase.auth.get_user(token)` |
| No FK from user_profiles.user_id to auth.users | Seed users don't exist in auth.users; FK would block seed script inserts | ✓ Good — service role key bypasses RLS; seed script works without auth.users rows |
| 95th-pct clip normalization for interaction scores | Prevents superuser collapse (one highly-active user skewing everyone else's scores to near-zero) | ✓ Good — `np.percentile(method='lower')` picks actual observed data point as cap |
| AsyncIOScheduler with CronTrigger per timezone | DB query at startup for unique timezones; re-query at fire time for current user list — handles user additions without restart | ✓ Good — `replace_existing=True` safe for restarts; per-user try/except prevents one failure from aborting batch |

---
*Last updated: 2026-02-23 after v1.0 milestone*
