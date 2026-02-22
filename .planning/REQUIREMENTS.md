# Requirements: SixDegrees — People Map Algorithm Milestone

**Defined:** 2026-02-22
**Core Value:** The People Map — every user is always at (0,0), all others positioned by profile similarity + interaction intensity, updated daily

---

## v1 Requirements

Requirements for this milestone. All are backend/algorithm — no frontend UI implementation.

### Database Schema

- [x] **DB-01**: `user_profiles` table exists in Supabase with fields: user_id (UUID), display_name, interests (text[]), location_city, location_state, age, languages (text[]), field_of_study, industry, education_level, timezone, updated_at
- [x] **DB-02**: `interactions` table exists in Supabase with fields: user_id_a (UUID), user_id_b (UUID), likes_count, comments_count, dm_count, last_updated; pair stored in canonical order (a < b)
- [x] **DB-03**: `map_coordinates` table exists in Supabase with fields: id, center_user_id (UUID), other_user_id (UUID), x (float), y (float), tier (1/2/3), computed_at, is_current (boolean)
- [x] **DB-04**: `map_coordinates` has index on (center_user_id, is_current) for fast API reads
- [x] **DB-05**: Seed script populates at least 15 mock users with varied profiles (diverse interests, locations, ages) and seeded interaction counts into Supabase

### Interaction Scoring Module

- [ ] **INT-01**: Interaction score computation reads weights from a dict config (`INTERACTION_WEIGHTS`) so adding a new interaction type requires only adding a column + a dict entry
- [ ] **INT-02**: Each interaction type is normalized independently using min-max normalization with 95th-percentile clipping before normalization (prevents superuser collapse)
- [ ] **INT-03**: Final interaction score per pair is a weighted sum of normalized individual type scores, producing a value in [0, 1]
- [ ] **INT-04**: Missing pairs (no interactions between two users) produce interaction_score = 0.0 (no special case needed)

### Distance Matrix

- [ ] **DIST-01**: Combined distance formula: `distance(i,j) = α × profile_distance(i,j) + β × (1 - interaction_score(i,j))`
- [ ] **DIST-02**: α and β are stored in `backend/config/algorithm.py` with defaults α=0.6, β=0.4; no magic numbers in algorithm code
- [ ] **DIST-03**: Profile distance computation preserves existing field weights (interests 35%, location 20%, languages 15%, field_of_study 10%, industry 10%, education 5%, age 5%)
- [ ] **DIST-04**: Resulting NxN distance matrix has values in [0, 1], is symmetric, and has zeros on diagonal

### t-SNE Projection

- [ ] **TSNE-01**: t-SNE replaces PCA for 2D coordinate projection; uses `sklearn.manifold.TSNE` with `metric='precomputed'`, `init='random'`, `random_state=42`
- [ ] **TSNE-02**: Perplexity is computed dynamically: `perplexity = min(30, max(5, int(sqrt(N))))` where N is number of users
- [ ] **TSNE-03**: Pipeline raises a clear error if N < 10 (t-SNE unstable below this threshold)
- [ ] **TSNE-04**: Raw t-SNE coordinates (before origin translation) are preserved for potential future Procrustes alignment

### Origin Translation & Tier Assignment

- [ ] **ORIG-01**: After t-SNE, coordinates are translated so the requesting user is at exactly (0.0, 0.0) by subtracting their raw coordinates from all users' coordinates
- [ ] **ORIG-02**: Tier assignment uses existing KNN logic: Tier 1 = 5 nearest, Tier 2 = next 10, Tier 3 = all within distance threshold; the requesting user themselves is included at (0,0) as Tier 1
- [ ] **ORIG-03**: Origin translation is applied independently per requesting user (each user gets their own translated coordinate set)

### Data Access Layer

- [ ] **DATA-01**: `data_fetcher.py` reads all user profiles from `user_profiles` table via Supabase Python client
- [ ] **DATA-02**: `data_fetcher.py` reads all interaction counts from `interactions` table for the set of user_ids being processed
- [ ] **DATA-03**: Backend uses service role key (not anon key) to bypass Supabase RLS

### Coordinate Storage

- [ ] **STORE-01**: After computing new coordinates, the write step marks all existing `is_current=true` rows for that center_user_id as `is_current=false` before inserting new rows
- [ ] **STORE-02**: Previous coordinate rows are retained (not deleted) to support future animation delta computation
- [ ] **STORE-03**: Each write stores both the requesting user themselves at (0,0) and all other users in the coordinate set

### API Endpoint

- [ ] **API-01**: `GET /map/{user_id}` returns precomputed coordinates from `map_coordinates` table — no live computation at request time
- [ ] **API-02**: Response format: `{ user_id, computed_at, coordinates: [{ user_id, x, y, tier, display_name }] }`
- [ ] **API-03**: The requesting user always appears in the coordinates list at (0.0, 0.0)
- [ ] **API-04**: If user_id has no precomputed map, returns 404 with message "Map not yet computed for this user"
- [ ] **API-05**: `POST /map/trigger/{user_id}` manually triggers pipeline recomputation for a single user (for testing/demo)

### Batch Scheduler

- [ ] **SCHED-01**: APScheduler (AsyncIOScheduler) starts with the FastAPI app via lifespan context manager
- [ ] **SCHED-02**: Scheduler registers one CronTrigger per unique timezone in the `user_profiles` table, firing at 19:00 in that timezone
- [ ] **SCHED-03**: On trigger, the scheduler groups all users with that timezone and runs the full pipeline for all of them
- [ ] **SCHED-04**: Single-worker constraint is documented: multi-worker uvicorn causes double-firing (known limitation, not fixed this milestone)

### Demo Deliverables

- [ ] **DEMO-01**: `scripts/test_map.py` is a standalone Python script that seeds mock data, runs the full pipeline, and plots a 2D scatter plot with matplotlib; dots labeled by display_name and color-coded by tier
- [ ] **DEMO-02**: `scripts/people_map_demo.ipynb` is a Jupyter notebook with per-stage explanations and inline plots; runs end-to-end with a single "Run All" command
- [ ] **DEMO-03**: Both scripts demonstrate sensitivity: increasing interaction count between two users moves them visibly closer; changing profile interests moves users relative to their interest cluster
- [ ] **DEMO-04**: Both scripts connect to the real Supabase instance (using `.env` credentials) and work with the seeded mock data

### Write API Endpoints

All frontend data writes go through the backend — no direct frontend → Supabase writes for application data. Frontend only calls Supabase directly for Auth.

- [ ] **AUTH-01**: Backend validates the Supabase JWT on all write endpoints using `supabase.auth.get_user(token)`; returns HTTP 401 for missing or invalid tokens
- [ ] **WRITE-01**: `POST /interactions/like` — accepts `{ target_user_id }` in body; validates JWT to identify acting user; upserts `interactions` row (canonical pair order) incrementing `likes_count`
- [ ] **WRITE-02**: `POST /interactions/comment` — accepts `{ target_user_id }` in body; validates JWT; upserts `interactions` row incrementing `comments_count`
- [ ] **WRITE-03**: `POST /interactions/dm` — accepts `{ target_user_id }` in body; validates JWT; upserts `interactions` row incrementing `dm_count`
- [ ] **WRITE-04**: `PUT /profile` — accepts profile fields in body; validates JWT; creates or updates the authenticated user's row in `user_profiles`; user can only update their own profile

### Frontend API Contract Document

- [ ] **SPEC-01**: `docs/API_CONTRACT.md` documents all endpoints: `GET /map/{user_id}` response format, all write endpoint request/response formats, auth header requirement, and error shapes
- [ ] **SPEC-02**: `docs/DB_SCHEMA.md` documents the table schemas — for reference only; frontend does not write directly to any table

---

## v2 Requirements

Deferred to future milestone.

### Animation System

- **ANIM-01**: Frontend animated transition between old and new coordinate sets (delta computed from is_current=false rows)
- **ANIM-02**: Procrustes alignment to minimize visual rotation/flip between daily map updates

### Scale & Performance

- **SCALE-01**: openTSNE for N > 5000 users (faster approximation algorithm)
- **SCALE-02**: APScheduler with PostgreSQL job store for multi-worker deployments
- **SCALE-03**: Coordinate delta compression (only store changed positions)

### Algorithm Enhancements

- **ALG-01**: New interaction types (profile view time, reaction types, shared post engagement) via config-only addition
- **ALG-02**: Time decay on interaction scores (recent interactions weighted more than old ones)

---

## Out of Scope

| Feature | Reason |
|---------|--------|
| Frontend People Map rendering | Frontend team's responsibility — this milestone produces the API contract |
| Social feed UI (posts/likes as visible features) | Backend-only milestone; write endpoints exist but no feed UI |
| Profile creation/editing UI | Backend `PUT /profile` endpoint exists; no frontend UI |
| DM messaging UI | Backend records `dm_count` via `POST /interactions/dm`; no messaging UI |
| Real-time map updates | Architecture supports via batch; real-time is out of scope |
| Redis / Celery | APScheduler is sufficient; added complexity not justified |
| Docker / deployment config | Local dev only |
| Full production test suite | Demo scripts only; no pytest suite required |
| Admin/moderation features | Not this milestone |

---

## Traceability

| Requirement | Phase | Phase Name | Status |
|-------------|-------|------------|--------|
| DB-01 | Phase 1 | Database Foundation | Complete |
| DB-02 | Phase 1 | Database Foundation | Complete |
| DB-03 | Phase 1 | Database Foundation | Complete |
| DB-04 | Phase 1 | Database Foundation | Complete |
| DB-05 | Phase 1 | Database Foundation | Pending |
| INT-01 | Phase 2 | Core Algorithm | Pending |
| INT-02 | Phase 2 | Core Algorithm | Pending |
| INT-03 | Phase 2 | Core Algorithm | Pending |
| INT-04 | Phase 2 | Core Algorithm | Pending |
| DIST-01 | Phase 2 | Core Algorithm | Pending |
| DIST-02 | Phase 2 | Core Algorithm | Pending |
| DIST-03 | Phase 2 | Core Algorithm | Pending |
| DIST-04 | Phase 2 | Core Algorithm | Pending |
| TSNE-01 | Phase 2 | Core Algorithm | Pending |
| TSNE-02 | Phase 2 | Core Algorithm | Pending |
| TSNE-03 | Phase 2 | Core Algorithm | Pending |
| TSNE-04 | Phase 2 | Core Algorithm | Pending |
| ORIG-01 | Phase 2 | Core Algorithm | Pending |
| ORIG-02 | Phase 2 | Core Algorithm | Pending |
| ORIG-03 | Phase 2 | Core Algorithm | Pending |
| DATA-01 | Phase 3 | Pipeline Integration | Pending |
| DATA-02 | Phase 3 | Pipeline Integration | Pending |
| DATA-03 | Phase 3 | Pipeline Integration | Pending |
| STORE-01 | Phase 3 | Pipeline Integration | Pending |
| STORE-02 | Phase 3 | Pipeline Integration | Pending |
| STORE-03 | Phase 3 | Pipeline Integration | Pending |
| API-01 | Phase 4 | API and Scheduler | Pending |
| API-02 | Phase 4 | API and Scheduler | Pending |
| API-03 | Phase 4 | API and Scheduler | Pending |
| API-04 | Phase 4 | API and Scheduler | Pending |
| API-05 | Phase 4 | API and Scheduler | Pending |
| SCHED-01 | Phase 4 | API and Scheduler | Pending |
| SCHED-02 | Phase 4 | API and Scheduler | Pending |
| SCHED-03 | Phase 4 | API and Scheduler | Pending |
| SCHED-04 | Phase 4 | API and Scheduler | Pending |
| AUTH-01 | Phase 4 | API and Scheduler | Pending |
| WRITE-01 | Phase 4 | API and Scheduler | Pending |
| WRITE-02 | Phase 4 | API and Scheduler | Pending |
| WRITE-03 | Phase 4 | API and Scheduler | Pending |
| WRITE-04 | Phase 4 | API and Scheduler | Pending |
| DEMO-01 | Phase 5 | Demo and Docs | Pending |
| DEMO-02 | Phase 5 | Demo and Docs | Pending |
| DEMO-03 | Phase 5 | Demo and Docs | Pending |
| DEMO-04 | Phase 5 | Demo and Docs | Pending |
| SPEC-01 | Phase 5 | Demo and Docs | Pending |
| SPEC-02 | Phase 5 | Demo and Docs | Pending |

**Coverage:**
- v1 requirements: 46 total (41 original + AUTH-01, WRITE-01–04, SPEC-01 and SPEC-02 updated)
- Mapped to phases: 46/46
- Unmapped: 0 ✓

---
*Requirements defined: 2026-02-22*
*Last updated: 2026-02-22 — DB-01 through DB-04 marked Complete (plan 01-01 finished)*
