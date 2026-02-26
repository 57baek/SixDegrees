# Architecture

**Analysis Date:** 2026-02-26

## Pattern Overview

**Overall:** Monorepo with split frontend/backend, where Vue directly uses Supabase for social content and FastAPI handles authenticated profile/match/map domain APIs plus scheduled map computation.

**Key Characteristics:**
- Keep UI composition and navigation in `frontend/src/views/`, `frontend/src/components/`, and `frontend/src/router/index.js`.
- Keep HTTP boundary logic in `backend/routes/*.py`, with auth centralized in `backend/routes/deps.py`.
- Keep algorithmic and orchestration logic in `backend/services/matching/` and `backend/services/map_pipeline/`, with database access through Supabase RPC wrappers.

## Layers

**Frontend Presentation Layer:**
- Purpose: Render pages/components and handle user interactions.
- Location: `frontend/src/views/`, `frontend/src/components/`, `frontend/src/App.vue`.
- Contains: Route views (`Home.vue`, `Login.vue`, `Profile.vue`, `ProfileSetup.vue`, `SignUp.vue`) and UI components (`CreatePost.vue`, `Post.vue`).
- Depends on: Vue runtime and router (`frontend/src/main.js`, `frontend/src/router/index.js`), Supabase browser client (`frontend/src/lib/supabase.js`).
- Used by: Browser entrypoint mounted from `frontend/src/main.js`.

**Frontend Routing/Auth Gate Layer:**
- Purpose: Control route-level access and app navigation.
- Location: `frontend/src/router/index.js`.
- Contains: Route table and `beforeEach` guard checking `localStorage` token.
- Depends on: Vue Router and view modules in `frontend/src/views/`.
- Used by: App bootstrap in `frontend/src/main.js`.

**Backend API Layer:**
- Purpose: Expose REST endpoints for profile, interactions, match, and map workflows.
- Location: `backend/app.py`, `backend/routes/profile.py`, `backend/routes/interactions.py`, `backend/routes/match.py`, `backend/routes/map.py`.
- Contains: FastAPI app setup, CORS setup, router registration, and endpoint handlers.
- Depends on: Auth dependency (`backend/routes/deps.py`), Supabase client (`backend/config/supabase.py`), service modules (`backend/services/*`).
- Used by: Frontend API consumers and external HTTP clients.

**Backend Auth/Infra Layer:**
- Purpose: Shared infrastructure for JWT validation and Supabase client singleton.
- Location: `backend/routes/deps.py`, `backend/config/supabase.py`.
- Contains: `get_current_user` JWT validator and `get_supabase_client` accessor.
- Depends on: Supabase SDK/auth API and environment config loaded in `backend/config/supabase.py`.
- Used by: All authenticated routes in `backend/routes/*.py` and DB-facing services.

**Matching and Map Domain Layer:**
- Purpose: Execute profile similarity scoring and map coordinate pipeline.
- Location: `backend/services/matching/`, `backend/services/map_pipeline/`, `backend/config/algorithm.py`, `backend/models/user.py`.
- Contains: Pure math/scoring functions, t-SNE projection, origin translation, data fetch/write orchestration, scheduler jobs.
- Depends on: Numpy/scikit-learn, model definitions, Supabase fetch/write adapters.
- Used by: `backend/routes/match.py`, `backend/routes/map.py`, and startup scheduler in `backend/app.py`.

**Database Contract Layer:**
- Purpose: Define SQL schema, RPCs, triggers, and RLS expectations consumed by frontend/backend.
- Location: `backend/sql/setup_tables.sql`, `backend/sql/add_increment_interaction_rpc.sql`, `backend/sql/v1.1_phase6_db_cleanup.sql`, `backend/sql/v1.1_phase6_rls_policies.sql`, `backend/sql/v1.2_phase14_add_timezone_to_profiles.sql`.
- Contains: Table definitions, canonical interaction constraints, RPC functions, trigger functions, policy rules.
- Depends on: Supabase Postgres.
- Used by: Supabase RPC calls in `backend/routes/*.py`, `backend/services/map_pipeline/*.py`, and direct frontend Supabase calls in `frontend/src/views/*.vue`.

## Data Flow

**Authenticated Backend Route Flow (`/profile`, `/match`, `/interactions`, `/map`):**

1. Client sends HTTP request to FastAPI in `backend/app.py` via routers in `backend/routes/*.py`.
2. Route dependency `get_current_user` in `backend/routes/deps.py` validates Bearer token through Supabase auth.
3. Route handler executes Supabase RPC calls (`backend/routes/profile.py`, `backend/routes/interactions.py`, `backend/routes/match.py`, `backend/routes/map.py`) and/or invokes service orchestration (`backend/services/map_pipeline/__init__.py`).
4. Handler returns stable JSON payloads or mapped HTTP errors (`HTTPException`).

**Map Pipeline Flow (trigger + scheduled):**

1. Trigger path (`POST /map/trigger/{user_id}` in `backend/routes/map.py`) or scheduled path (`setup_scheduler` in `backend/services/map_pipeline/scheduler.py`) calls `run_pipeline_for_user` in `backend/services/map_pipeline/__init__.py`.
2. `fetch_all` in `backend/services/map_pipeline/data_fetcher.py` loads profiles and interaction counts from Supabase RPCs.
3. `run_pipeline` in `backend/services/map_pipeline/pipeline.py` computes interaction matrix -> combined distance -> t-SNE projection -> translated coordinates/tier assignment using `interaction.py`, `scoring.py`, `tsne_projector.py`, `origin_translator.py`.
4. `write_coordinates` in `backend/services/map_pipeline/coord_writer.py` archives old rows and inserts current rows through RPCs.

**Frontend Social Flow (direct Supabase):**

1. Browser app bootstraps in `frontend/src/main.js` and loads routes from `frontend/src/router/index.js`.
2. Views/components use `supabase` client from `frontend/src/lib/supabase.js` for auth and content RPC/table operations.
3. UI updates local reactive state (`ref`, `computed`) in `frontend/src/views/Home.vue`, `frontend/src/views/Profile.vue`, `frontend/src/components/Post.vue`, and `frontend/src/components/CreatePost.vue`.

**State Management:**
- Use component-local Vue state (`ref`, `computed`) in `frontend/src/views/*.vue` and `frontend/src/components/*.vue`; no global store module is present.
- Use backend stateless request handling with derived data per request in `backend/routes/*.py` and pure computation modules in `backend/services/map_pipeline/pipeline.py` and `backend/services/matching/scoring.py`.

## Key Abstractions

**Authenticated User Dependency:**
- Purpose: Provide a single JWT-authenticated user id boundary for protected endpoints.
- Examples: `backend/routes/deps.py`, usage in `backend/routes/profile.py`, `backend/routes/interactions.py`, `backend/routes/match.py`, `backend/routes/map.py`.
- Pattern: FastAPI dependency injection with `Depends(get_current_user)`.

**User Profile Domain Model:**
- Purpose: Normalize profile records for similarity and map computation.
- Examples: `backend/models/user.py`, constructors in `backend/routes/match.py` and `backend/services/map_pipeline/data_fetcher.py`.
- Pattern: Pydantic `BaseModel` used as typed transfer object between API/service layers.

**Pure Pipeline Stages:**
- Purpose: Keep map algorithm stages deterministic and testable.
- Examples: `backend/services/map_pipeline/interaction.py`, `backend/services/map_pipeline/scoring.py`, `backend/services/map_pipeline/tsne_projector.py`, `backend/services/map_pipeline/origin_translator.py`, orchestrator `backend/services/map_pipeline/pipeline.py`.
- Pattern: Functional composition (input structs/arrays -> output structs/arrays) with no direct DB writes.

**DB-Connected Pipeline Orchestrator:**
- Purpose: Bridge Supabase I/O and pure map pipeline execution.
- Examples: `backend/services/map_pipeline/__init__.py`, `backend/services/map_pipeline/data_fetcher.py`, `backend/services/map_pipeline/coord_writer.py`.
- Pattern: Read -> compute -> write workflow adapter around pure computation core.

## Entry Points

**FastAPI Application:**
- Location: `backend/app.py`.
- Triggers: `uvicorn app:app --reload` from `backend/`.
- Responsibilities: Build app instance, register routers, configure CORS, start/stop APScheduler during lifespan.

**Scheduler Registration:**
- Location: `backend/services/map_pipeline/scheduler.py`.
- Triggers: Called from FastAPI lifespan in `backend/app.py` at startup.
- Responsibilities: Query distinct timezones, register cron jobs, execute per-timezone map pipeline batches.

**Vue Application Bootstrap:**
- Location: `frontend/src/main.js`.
- Triggers: Vite app start/build from `frontend/package.json` scripts.
- Responsibilities: Mount root Vue app and install router.

## Error Handling

**Strategy:** Convert expected domain/auth failures into explicit transport-level errors and propagate unexpected lower-level exceptions to fail fast.

**Patterns:**
- Use `HTTPException` in route handlers for auth/ownership/not-found/validation failures in `backend/routes/deps.py`, `backend/routes/map.py`, `backend/routes/profile.py`, `backend/routes/interactions.py`, `backend/routes/match.py`.
- Raise `ValueError` in algorithm/service layer for invalid pipeline preconditions in `backend/services/map_pipeline/pipeline.py` and `backend/services/map_pipeline/tsne_projector.py`, then map to HTTP 422 in `backend/routes/map.py`.

## Cross-Cutting Concerns

**Logging:** Structured scheduler logs via Python `logging` in `backend/services/map_pipeline/scheduler.py`; UI/debug logs via `console` in `frontend/src/main.js`, `frontend/src/views/*.vue`, and `frontend/src/components/*.vue`.
**Validation:** Request payload validation via Pydantic models in `backend/routes/profile.py` and `backend/routes/interactions.py`; simple client-side input checks in `frontend/src/views/SignUp.vue` and `frontend/src/views/ProfileSetup.vue`.
**Authentication:** Backend JWT enforcement through `Depends(get_current_user)` in `backend/routes/*.py`; frontend route guard and Supabase auth session usage in `frontend/src/router/index.js` and `frontend/src/lib/supabase.js`.

---

*Architecture analysis: 2026-02-26*
