# SixDegrees

A social networking app built around a 2D People Map. Users are plotted in space based on profile similarity and interaction history - the closer two people are on the map, the more similar they are. Matching uses UMAP dimensionality reduction over a combined profile distance + interaction distance matrix.

## Try It Out

Visit the live app at **https://six-degrees-nine.vercel.app**

Want to explore without signing up? Use the demo account:

| Field | Value |
|-------|-------|
| Email | `aaaa@gmail.com` |
| Password | `AAAAaaaa1234!` |

The demo account is a pre-seeded user with friends, posts, and a People Map already built. Feel free to poke around - like posts, check the map, or use matching.

---

## How the People Map Works

The People Map places every user at a point in 2D space. The rule is simple: **the closer two people are on the map, the more similar they are** - in interests, background, and how much they interact. This section explains exactly how that position is computed.

---

### Why a Global Coordinate System?

Computing similarity between two users requires comparing their profiles and interactions - that's an O(N²) operation (every pair). Rather than doing this on-demand each time someone opens the map (which would be slow and redundant), we run the full pipeline once per day for **all N users simultaneously**, producing a single shared coordinate space. Every user's (x, y) position is stored in `public.user_positions`.

When you open the map, the backend reads your position and those of your connections from the database - no recomputation needed. This is orders of magnitude faster than per-user, per-request matching.

---

### Step 1 - Profile Distance Matrix

For every pair of users (i, j), we compute a **profile similarity score** from 0 to 1 across six fields:

| Field | Method | Weight |
|-------|--------|--------|
| Interests + Bio | **AI embedding similarity** (see below) | 0.40 |
| Location | Tiered: same city → 1.0 / same state → 0.5 / different → 0.0 | 0.20 |
| Languages | Jaccard similarity on language sets | 0.15 |
| Education (field of study) | Tiered categorical: exact match → 1.0 / same broad category → 0.5 | 0.10 |
| Industry | Tiered categorical: exact match → 1.0 / same broad category → 0.5 | 0.10 |
| Age | Inverse distance: 1 / (1 + \|age_a − age_b\|) | 0.05 |

#### AI Embedding Model (the core of interest matching)

Interests and bio are scored using a **pre-trained sentence-transformer model** (`all-MiniLM-L6-v2`, 384 dimensions). Each user's interests and bio are concatenated into a single text string and encoded into a 384-dimensional vector. Similarity between two users is then the **cosine similarity** between their vectors.

This means the system understands *semantic meaning*, not just exact keyword overlap. "Hiking" and "trail running" score high similarity even though they share no words. "Machine learning" and "AI" are treated as near-synonyms. Plain keyword matching (Jaccard) cannot do this - the embedding model is what makes interest matching intelligent.

The weighted sum across all fields gives a scalar **profile similarity** ∈ [0, 1]. We invert it to get **profile distance**:

```
profile_dist(i, j) = 1 − profile_similarity(i, j)
```

This produces an N×N symmetric matrix with zeros on the diagonal.

---

### Step 2 - Interaction Distance Matrix

For every pair (i, j), we look up their interaction history:

```
raw_score(i, j) = likes_count × 0.5 + comments_count × 0.5
```

We normalize across all pairs by dividing by the maximum raw score observed, bringing every value into [0, 1]. More interaction → smaller distance:

```
interaction_dist(i, j) = 1 − (raw_score(i, j) / max_raw_score)
```

Users who have never interacted get `interaction_dist = 1.0` (maximum distance).

---

### Step 3 - Combined Distance Matrix

The two N×N matrices are blended with fixed weights (α = 0.6, β = 0.4):

```
combined_dist(i, j) = 0.6 × profile_dist(i, j) + 0.4 × interaction_dist(i, j)
```

The result is clipped to [0, 1] and the diagonal is forced to 0 (every user is distance 0 from themselves). This single matrix encodes the full pairwise similarity of the entire user base.

---

### Step 4 - UMAP Projection to 2D

UMAP (Uniform Manifold Approximation and Projection) takes the N×N precomputed distance matrix and projects every user to a point in 2D space, preserving the neighbourhood structure: users who are close in the high-dimensional distance space end up close on the map.

Key parameters:

| Parameter | Value | Effect |
|-----------|-------|--------|
| `metric` | `"precomputed"` | Uses our distance matrix directly |
| `n_neighbors` | 15 | How many nearby users each point considers when learning the manifold |
| `min_dist` | 0.1 | How tightly points are allowed to cluster together |

The output is an N×2 array of (x, y) coordinates - one point per user, all in the same global coordinate space.

---

### Step 5 - Normalisation & Write

UMAP's raw output is unanchored - the coordinate scale, translation, and orientation can differ between runs even with the same random seed. Before storing, we normalise each axis to **[0, 1]**:

```
x_norm = (x − x_min) / (x_max − x_min)
y_norm = (y − y_min) / (y_max − y_min)
```

This keeps coordinates comparable across runs and means a full profile change is reflected immediately the next time you hit **Refresh Map** - there is no incremental drift.

The final coordinates are upserted into `public.user_positions` (one row per user).

---

### Step 6 - Ego Map (What You See)

When you open the People Map, the backend calls `build_ego_map(your_id)`:

1. Reads **all** positions from `user_positions`.
2. Fetches your social graph up to 3 degrees via `extended_friends(3)`.
3. Translates every coordinate so **you are at (0, 0)** - everyone else's position is relative to yours.
4. Assigns a tier to each person based on their friendship distance to you (tier 1 = Inner Circle, tier 2 = 2nd Degree, tier 3 = 3rd Degree).

The frontend receives this translated, tiered list and renders it as rings around you. You never see the raw global coordinates - only positions relative to your own.

---

### Pipeline Summary

```
All N user profiles + interactions
         │
         ▼
Step 1: Profile distance matrix        N×N  O(N²)
Step 2: Interaction distance matrix    N×N  O(N²)
Step 3: Combined distance matrix       N×N  O(N²)
         │
         ▼
Step 4: UMAP projection → N×2 coordinates
         │
         ▼
Step 5: Normalise to [0,1] → upsert to user_positions
         │
         ▼
Step 6: On map open → ego map (translate + tier)   O(1) DB reads
```

The expensive O(N²) work happens once per day at UTC 00:00. Every individual map load is a cheap database read.

---

## Architecture

```
Frontend (Vue 3)
    ├── Social features (posts, likes, comments, friends)
    │       └── Supabase RPCs directly (FastAPI bypassed)
    └── Map + matching (coordinates, similarity scores)
            └── FastAPI REST API → Supabase internally
```

Two data paths:
- **Social features** - frontend calls Supabase PostgreSQL functions (RPCs) directly. FastAPI is not involved.
- **Map + matching** - frontend calls FastAPI endpoints, which read/write Supabase internally using a service-role key.

## Deployment

The app is deployed as two separate services:

**Live app:** https://six-degrees-nine.vercel.app

### Cost & Performance Notes

The backend runs on Render's **free tier (512MB RAM)**. To stay within the memory limit:

- Heavy ML libraries (`umap-learn`, `sentence-transformers`) are **lazy-loaded** - they are not imported at startup, only when the pipeline actually runs.
- The map pipeline runs automatically once per day at **UTC 00:00** via APScheduler. This scheduled run recomputes positions for all users and writes them to `user_positions`. Individual map loads are always fast - they read precomputed positions from the database, not recompute them.

---

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
   - `public.profiles` - writable view over `private.profiles`
   - `public.interactions` - interaction counters
   - `public.user_positions` - UMAP map coordinates
   - `public.pipeline_runs` - pipeline diagnostics log

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
| `SUPABASE_KEY` | Service-role key (full DB access - keep secret) |
| `ALLOWED_ORIGINS` | Comma-separated frontend URLs for CORS. Defaults to `http://localhost:5173`. |
| `GLOBAL_COMPUTE_ENABLED` | Set to `true` to enable the scheduled UMAP pipeline. Default: `false`. |

Start the server:

```bash
# IMPORTANT: single worker only - APScheduler fires N times with N workers
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

## Friends & Degrees System

### Nicknames

Every user picks a unique nickname during onboarding. Nicknames are the primary way to find and connect with other people - friend requests are sent by nickname, not by searching a name or email.

### How Friendship Works

Friendship on SixDegrees is **mutual and opt-in**:

1. User A sends a friend request to User B using B's nickname.
2. User B receives the request on their Home feed and chooses to **Accept** or **Reject** it.
3. Only after B accepts does the connection become active - both users are then friends with each other simultaneously. There is no one-sided following; friendship is always a two-way bond.

If User A changes their mind before B responds, they can rescind the request. If B rejects it, no connection is created.

### Degrees of Separation (Tiers)

Connections are organised into tiers based on social distance:

| Tier | Label | Who it includes |
|------|-------|-----------------|
| 1 | **Inner Circle** | Your direct, mutual friends - people who have accepted (or whose request you accepted) |
| 2 | **Extended Network** | Friends-of-friends - people connected to your Tier 1 friends |
| 3 | **Wider Community** | Two hops away - friends of your Tier 2 connections |

This mirrors the classic "six degrees of separation" idea: the further the tier, the more indirect the connection.

### What Tiers Affect

- **Posts** are tagged with a visibility tier (1, 2, or 3) when created. A Tier 1 post is only visible to your Inner Circle; a Tier 3 post reaches the Wider Community.
- **The People Map** plots all users in 2D space - users closer to you on the map are more similar to you based on profile and interaction history, regardless of tier.
- **Matching** surfaces the most compatible users from across all tiers.

## Scheduled Jobs

**People Map recalculation:** The UMAP pipeline runs automatically every day at **UTC 00:00**, recomputing positions for all users. This requires `GLOBAL_COMPUTE_ENABLED=true` in `backend/.env` and the server running in single-worker mode. Results are written to `public.user_positions` and become visible immediately on the next map load.

## Key Constraints

**Single-worker only:** Never run `uvicorn --workers N`. APScheduler fires once per worker, causing duplicate pipeline runs. Always use `--reload`.

**Private schema architecture:** User-facing tables (`profiles`, `posts`, etc.) live in the `private` Supabase schema. The backend reads/writes profiles through a public view (`public.profiles`) with an INSTEAD OF trigger that routes writes back to `private.profiles`. Always use `sb.table("profiles")` - never bypass the view.

**Two data-flow paths:** Social features bypass FastAPI entirely. Map and matching go through FastAPI. Do not add social feature logic to the FastAPI backend.

## Project Structure

```
backend/
  app.py              # FastAPI app, CORS, lifespan (APScheduler)
  config/settings.py  # All config: Supabase client, weights, UMAP params
  routes/             # HTTP layer only - no business logic
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
