# SixDegrees

A social networking app built around a 2D People Map. Users are plotted in space based on profile similarity and interaction history — the closer two people are on the map, the more similar they are. Matching uses UMAP dimensionality reduction over a combined profile distance + interaction distance matrix.

## Architecture

```
Frontend (Vue 3)
    ├── Social features (posts, likes, comments, friends)
    │       └── Supabase RPCs directly (FastAPI bypassed)
    └── Map + matching (coordinates, similarity scores)
            └── FastAPI REST API → Supabase internally
```

Two data paths:
- **Social features** — frontend calls Supabase PostgreSQL functions (RPCs) directly. FastAPI is not involved.
- **Map + matching** — frontend calls FastAPI endpoints, which read/write Supabase internally using a service-role key.

## Prerequisites

- Python 3.11+
- Node 18+
- A [Supabase](https://supabase.com) project (free tier works)

## Supabase Setup

1. Create a new Supabase project.

2. Enable the `private` schema. In the Supabase SQL editor:
   ```sql
   ALTER ROLE authenticator SET search_path TO public, private;
   ```

3. Create the `private.profiles` table (and related tables: `posts`, `likes`, `comments`, `friend_requests`, `reports`) in your Supabase project.

4. Run `backend/sql/02_schema.sql` in the SQL editor. This creates:
   - `public.profiles` — writable view over `private.profiles`
   - `public.interactions` — interaction counters
   - `public.user_positions` — UMAP map coordinates
   - `public.pipeline_runs` — pipeline diagnostics log

5. Create a Storage bucket named **`post-images`** with public read access:
   Dashboard → Storage → New bucket → Name: `post-images` → Public: on

6. Note your project's **URL**, **anon/public key**, and **service-role key** from:
   Dashboard → Settings → API

## Backend Setup

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `backend/.env`:

| Variable | Description |
|----------|-------------|
| `SUPABASE_URL` | Your Supabase project URL |
| `SUPABASE_KEY` | Service-role key (full DB access — keep secret) |
| `ALLOWED_ORIGINS` | Comma-separated frontend URLs for CORS. Defaults to `http://localhost:5173`. |
| `GLOBAL_COMPUTE_ENABLED` | Set to `true` to enable the scheduled UMAP pipeline. Default: `false`. |

Start the server:

```bash
# IMPORTANT: single worker only — APScheduler fires N times with N workers
uvicorn app:app --reload
```

## Frontend Setup

```bash
cd frontend
npm install
cp .env.example .env
```

Edit `frontend/.env`:

| Variable | Description |
|----------|-------------|
| `VITE_SUPABASE_URL` | Your Supabase project URL |
| `VITE_SUPABASE_ANON_KEY` | Anon/public key (safe to expose in frontend) |
| `VITE_API_URL` | FastAPI backend URL (e.g., `http://localhost:8000`) |

Start the dev server:

```bash
npm run dev   # http://localhost:5173
```

## Running Tests

```bash
cd backend
source venv/bin/activate
python -m pytest -q                          # all tests
python -m pytest -q tests/map/              # map pipeline only
python -m pytest --cov=. --cov-report=term-missing  # with coverage
```

## Key Constraints

**Single-worker only:** Never run `uvicorn --workers N`. APScheduler fires once per worker, causing duplicate pipeline runs. Always use `--reload`.

**Private schema architecture:** User-facing tables (`profiles`, `posts`, etc.) live in the `private` Supabase schema. The backend reads/writes profiles through a public view (`public.profiles`) with an INSTEAD OF trigger that routes writes back to `private.profiles`. Always use `sb.table("profiles")` — never bypass the view.

**Two data-flow paths:** Social features bypass FastAPI entirely. Map and matching go through FastAPI. Do not add social feature logic to the FastAPI backend.

## Project Structure

```
backend/
  app.py              # FastAPI app, CORS, lifespan (APScheduler)
  config/settings.py  # All config: Supabase client, weights, UMAP params
  routes/             # HTTP layer only — no business logic
  models/user.py      # UserProfile Pydantic model
  services/map/       # UMAP pipeline: fetcher → distance → projector → writer
  services/matching/  # Scoring, similarity, embedding (all-MiniLM-L6-v2)
  scripts/seed.py     # Seed 100 deterministic fake profiles
  sql/02_schema.sql   # Contributor DB setup script
  tests/              # 141 tests, all mocked (no live DB calls)

frontend/
  src/views/          # Page components (Home, Profile, PeopleMap, Match, etc.)
  src/components/     # Shared components (Post, CreatePost)
  src/router/         # Vue Router with auth guards
  src/lib/supabase.js # Supabase client init

demo/
  sixdegrees_demo.ipynb            # Eleanor/Brita two-case algorithm demo
  embedding_similarity_demo.ipynb  # Live embedding similarity demo
```
