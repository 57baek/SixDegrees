# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SixDegrees is a social networking platform built around a **People Map** — a personalized 2D visualization placing every user relative to you based on profile similarity + interaction intensity. You are always at (0, 0); closeness reflects how compatible your profiles are and how much you've interacted. The map updates daily via a batch job at 7pm per user's local timezone.

**Current milestone:** Backend algorithm pipeline — t-SNE people map with interaction data, batch scheduler, and demo deliverables. Frontend UI is out of scope for this milestone.

## Development Commands

### Frontend (Vue 3 + Vite)
```bash
cd frontend
npm install
npm run dev       # Dev server at http://localhost:5173
npm run build     # Production build → dist/
npm run preview   # Preview production build
```

### Backend (FastAPI)
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --reload   # Single worker only — multi-worker causes APScheduler double-firing
```

### Demo Scripts (once Phase 3+ complete)
```bash
python scripts/test_map.py              # Standalone matplotlib scatter plot
jupyter notebook scripts/people_map_demo.ipynb  # Interactive notebook
```

### Environment Setup
Both frontend and backend require `.env` files — copy from `.env.example` in each directory and fill in Supabase credentials. Backend must use the **service role key** (not anon key) to bypass RLS.

## Architecture

### Frontend (`frontend/src/`)
- **Vue Router** with an auth guard that checks `localStorage.supabase_token` before allowing access to protected routes
- **Supabase JS client** (`lib/supabase.js`) handles auth directly from the frontend — backend auth endpoints are not yet implemented
- **API calls** to the backend use Axios; Vite proxies `/api` → `http://localhost:8000`
- Home feed uses hardcoded mock data — posts/likes/comments DB tables do not exist yet

### Backend (`backend/`)
- **`app.py`** — FastAPI entry point; CORS for `localhost:5173`; APScheduler starts via `lifespan` context
- **`config/supabase.py`** — Supabase admin client (service role key); validates env vars at startup
- **`config/algorithm.py`** — Algorithm tuning constants: `ALPHA`, `BETA`, `INTERACTION_WEIGHTS` dict, `PROFILE_WEIGHTS`
- **`routes/match.py`** — Existing: user matches, graph coordinates, cache invalidation
- **`routes/map.py`** — New (Phase 4): `GET /map/{user_id}`, `POST /map/trigger/{user_id}`
- **`routes/interactions.py`** — New (Phase 4): `POST /interactions/like`, `POST /interactions/comment`, `POST /interactions/dm`
- **`routes/profile.py`** — New (Phase 4): `PUT /profile`
- **`routes/auth.py`** — Stub; not yet implemented (Supabase Auth handles login/session on frontend)
- **`models/user.py`** — Pydantic models: `UserProfile`, `MatchResult`

### Algorithm Pipeline

#### Existing (`backend/services/matching/`) — keep, extend
1. **`similarity.py`** — Per-field similarity scores (Jaccard, tiered, binary, inverse-distance)
2. **`scoring.py`** — Weighted N×N distance matrix (distance = 1 − similarity). Being extended to combine profile + interaction distance.
3. **`clustering.py`** — KNN tier assignment: Tier 1 = 5 nearest, Tier 2 = next 10, Tier 3 = within 0.75
4. **`visualization.py`** — **Being replaced**: PCA → t-SNE with `metric='precomputed'`

#### New Pipeline (`backend/services/map_pipeline/`) — this milestone
- **`data_fetcher.py`** — Reads `user_profiles` + `interactions` from Supabase
- **`interaction.py`** — Normalizes interaction counts (min-max with 95th-pct clipping), combines into interaction score using `INTERACTION_WEIGHTS` dict
- **`scoring.py`** — Combines profile distance + interaction score: `distance = α × profile_dist + β × (1 - interaction_score)`
- **`tsne_projector.py`** — `sklearn.manifold.TSNE(metric='precomputed', init='random', random_state=42)`; perplexity = `min(30, max(5, sqrt(N)))`; raises error if N < 10
- **`origin_translator.py`** — Shifts all coordinates so requesting user is at (0.0, 0.0)
- **`coord_writer.py`** — Marks previous rows `is_current=false`, inserts new rows; retains old rows for future animation delta
- **`scheduler.py`** — APScheduler timezone-grouped CronTriggers at 19:00 per timezone

### Write Pattern (Architecture Decision)

All application data writes go through the FastAPI backend — no direct frontend → Supabase writes:

```
Frontend auth:     Frontend → Supabase Auth directly          (login, session refresh)
Frontend reads:    Frontend → Supabase directly               (map_coordinates, user_profiles for display)
Frontend writes:   Frontend → Backend API → Supabase          (likes, comments, DMs, profile updates)
```

All write endpoints require a Supabase JWT in the `Authorization: Bearer <token>` header. Backend validates via `supabase.auth.get_user(token)`. Returns 401 for missing/invalid tokens, 403 if user attempts to modify another user's data.

### Database (Supabase PostgreSQL)

| Table | Status | Purpose |
|-------|--------|---------|
| `user_profiles` | To create (Phase 1) | Profile data for algorithm input; includes `timezone` field |
| `interactions` | To create (Phase 1) | Pairwise interaction counts (likes/comments/dm); canonical pair order (a < b) |
| `map_coordinates` | To create (Phase 1) | Precomputed (x, y, tier) per (center_user, other_user); `is_current` flag for versioning |
| `users` | Existing (partial) | Legacy — being superseded by `user_profiles` |
| `posts`/`likes`/`comments` | Not yet created | Out of scope for this milestone |

Supabase Auth is the only working auth mechanism (frontend calls it directly).

### Distance Formula

```
distance(i, j) = α × profile_distance(i, j) + β × (1 - interaction_score(i, j))
```

Defaults: `α=0.6, β=0.4`. Profile weights unchanged: interests 35%, location 20%, languages 15%, field_of_study 10%, industry 10%, education 5%, age 5%.

### Interaction Modularity

Adding a new interaction type requires **only**:
1. Add column to `interactions` table
2. Add entry to `INTERACTION_WEIGHTS` dict in `config/algorithm.py`

Zero logic changes anywhere else.

## Known Bugs

- `handleLogout()` in `Home.vue` is defined inside `loadPosts()` — scoping bug, logout crashes the app
- Existing `/match` routes have no auth validation — any user_id is served without verification (new write routes will have JWT validation; old match routes remain unprotected this milestone)
- CORS hardcoded to `localhost:5173` only

## Key Constraints

- **Single worker only**: `uvicorn app:app --reload` — multi-worker causes APScheduler to fire jobs N times
- **Scheduler**: APScheduler 3.x (not 4.x) with `AsyncIOScheduler` — no Redis, no Celery
- **t-SNE must use**: `metric='precomputed'`, `init='random'` (NOT 'pca'), `random_state=42`
- **Perplexity guard**: `perplexity = min(30, max(5, int(sqrt(N))))` — pipeline fails fast if N < 10
- **Interaction normalization**: clip at 95th percentile before min-max to prevent superuser collapse

## Planning Artifacts

`.planning/` directory contains the full project plan:
- `PROJECT.md` — project context and requirements
- `ROADMAP.md` — 5-phase roadmap
- `REQUIREMENTS.md` — 41 v1 requirements with traceability
- `research/` — stack, features, architecture, and pitfalls research
