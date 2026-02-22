# Roadmap: SixDegrees — People Map Algorithm Milestone

## Overview

This milestone delivers the backend algorithm pipeline that powers the People Map: a daily-computed 2D visualization placing every user relative to the requesting user based on profile similarity and interaction intensity. The work flows through five natural phases — database foundation, pure algorithm modules, pipeline integration (connecting algorithm to DB), serving layer (API + scheduler), and demo validation. The frontend team consumes the API contract produced at the end.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Database Foundation** - Create all Supabase tables and seed 15+ mock users with interaction data
- [ ] **Phase 2: Core Algorithm** - Build interaction scoring, combined distance matrix, t-SNE projection, and origin translation as pure computation modules
- [ ] **Phase 3: Pipeline Integration** - Wire algorithm to real DB data (fetcher reads user_profiles/interactions, writer stores map_coordinates)
- [ ] **Phase 4: API and Scheduler** - Expose map coordinates via GET; accept interaction events and profile writes via JWT-validated POST/PUT endpoints; schedule daily batch recomputation per timezone
- [ ] **Phase 5: Demo and Docs** - Validate algorithm with test_map.py + Jupyter notebook; publish API contract and DB schema docs

## Phase Details

### Phase 1: Database Foundation
**Goal**: All required Supabase tables exist with correct schema and are populated with realistic seed data so the algorithm pipeline has real inputs to process
**Depends on**: Nothing (first phase)
**Requirements**: DB-01, DB-02, DB-03, DB-04, DB-05
**Success Criteria** (what must be TRUE):
  1. Querying `user_profiles` returns at least 15 rows with varied interests, locations, ages, and languages
  2. Querying `interactions` returns seeded like/comment/dm counts between user pairs in canonical order (user_id_a < user_id_b)
  3. Querying `map_coordinates` with any center_user_id and `is_current=true` works (table exists, index present, initially empty)
  4. Backend service role key can read all three tables without RLS errors
**Plans**: 2 plans

Plans:
- [x] 01-01-PLAN.md — Write setup_tables.sql DDL + apply in Supabase dashboard (DB-01, DB-02, DB-03, DB-04)
- [ ] 01-02-PLAN.md — Write and run seed_db.py with 20 diverse users and interaction pairs (DB-05)

### Phase 2: Core Algorithm
**Goal**: The full computation pipeline — interaction scoring, combined distance matrix, t-SNE projection, and origin translation — runs correctly on in-memory test data and produces a verifiable 2D coordinate output
**Depends on**: Phase 1
**Requirements**: INT-01, INT-02, INT-03, INT-04, DIST-01, DIST-02, DIST-03, DIST-04, TSNE-01, TSNE-02, TSNE-03, TSNE-04, ORIG-01, ORIG-02, ORIG-03
**Success Criteria** (what must be TRUE):
  1. Adding a new interaction type requires only one new dict entry in `INTERACTION_WEIGHTS` and zero logic changes — verified by adding a dummy type and confirming it flows through scoring
  2. Two users with high shared interaction counts appear measurably closer on the 2D output than two users with zero interactions but identical profile similarity
  3. The requesting user's coordinates are exactly (0.0, 0.0) after origin translation; all other users are translated consistently
  4. Passing fewer than 10 users to the t-SNE step raises a clear descriptive error (not a cryptic sklearn crash)
  5. The NxN distance matrix is symmetric, has zeros on the diagonal, and all values are in [0, 1]
**Plans**: TBD

### Phase 3: Pipeline Integration
**Goal**: The algorithm reads real profile and interaction data from Supabase and writes computed coordinates back to `map_coordinates` — the pipeline runs end-to-end against the live database
**Depends on**: Phase 2
**Requirements**: DATA-01, DATA-02, DATA-03, STORE-01, STORE-02, STORE-03
**Success Criteria** (what must be TRUE):
  1. Running the full pipeline for a specific user_id produces rows in `map_coordinates` with `is_current=true` and correct x/y/tier values
  2. Running the pipeline a second time for the same user marks the previous rows `is_current=false` and inserts fresh rows — old rows are retained, not deleted
  3. The requesting user appears in `map_coordinates` at (0.0, 0.0) alongside all other users
**Plans**: TBD

### Phase 4: API and Scheduler
**Goal**: The People Map is accessible via HTTP, interaction events and profile data are written through backend endpoints with JWT validation, and daily batch recomputation runs automatically per user timezone
**Depends on**: Phase 3
**Requirements**: API-01, API-02, API-03, API-04, API-05, SCHED-01, SCHED-02, SCHED-03, SCHED-04, AUTH-01, WRITE-01, WRITE-02, WRITE-03, WRITE-04
**Success Criteria** (what must be TRUE):
  1. `GET /map/{user_id}` returns correct JSON with the requesting user at (0.0, 0.0) in the coordinates list
  2. `GET /map/{user_id}` for a user with no precomputed map returns HTTP 404 with message "Map not yet computed for this user"
  3. `POST /map/trigger/{user_id}` triggers recomputation and updated coordinates are immediately available
  4. `POST /interactions/like` with a valid JWT increments `likes_count` in `interactions`; same request without a JWT returns HTTP 401
  5. `PUT /profile` with a valid JWT creates or updates the user's row in `user_profiles`; attempting to update another user's profile returns HTTP 403
  6. FastAPI starts without errors and APScheduler registers CronTriggers matching unique timezones in `user_profiles`
**Plans**: TBD

### Phase 5: Demo and Docs
**Goal**: The algorithm's correctness is demonstrable through runnable scripts, and the frontend team has a complete written contract for what to read and write
**Depends on**: Phase 4
**Requirements**: DEMO-01, DEMO-02, DEMO-03, DEMO-04, SPEC-01, SPEC-02
**Success Criteria** (what must be TRUE):
  1. `python scripts/test_map.py` runs to completion against real Supabase and displays a matplotlib scatter plot with dots labeled by display_name and color-coded by tier (3 colors)
  2. Opening `scripts/people_map_demo.ipynb` and running all cells completes without errors and shows per-stage inline plots
  3. Increasing the seeded interaction count between two users and re-running either script produces a scatter plot where those two users are visibly closer than before
  4. `docs/API_CONTRACT.md` and `docs/DB_SCHEMA.md` exist and contain enough detail that the frontend team can implement without asking follow-up questions
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Database Foundation | 1/2 | In Progress | - |
| 2. Core Algorithm | 0/? | Not started | - |
| 3. Pipeline Integration | 0/? | Not started | - |
| 4. API and Scheduler | 0/? | Not started | - |
| 5. Demo and Docs | 0/? | Not started | - |
