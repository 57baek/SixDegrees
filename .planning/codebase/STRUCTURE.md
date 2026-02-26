# Codebase Structure

**Analysis Date:** 2026-02-26

## Directory Layout

```text
sixDegrees/
├── backend/                 # FastAPI API, domain services, SQL scripts, backend tests
│   ├── app.py               # FastAPI entrypoint and lifecycle wiring
│   ├── config/              # Supabase client and algorithm constants
│   ├── models/              # Shared backend Pydantic domain models
│   ├── routes/              # HTTP route modules by domain
│   ├── services/            # Matching and map pipeline computation/orchestration
│   ├── sql/                 # Schema/RPC/RLS migration and setup SQL files
│   ├── scripts/             # Operational scripts (seed data)
│   └── tests/               # Pytest suite for routes and map pipeline
├── frontend/                # Vue 3 + Vite client app
│   ├── src/                 # App source (views, components, router, lib)
│   ├── package.json         # Frontend scripts and dependencies
│   └── vite.config.js       # Vite dev server/build config
├── .planning/codebase/      # Generated codebase mapping documents
├── AGENTS.md                # Agent operational guidance for this repository
└── README.md                # Project readme (currently empty)
```

## Directory Purposes

**`backend/`:**
- Purpose: Backend application boundary and domain execution surface.
- Contains: FastAPI app (`backend/app.py`), API routes (`backend/routes/*.py`), services (`backend/services/**/*.py`), SQL scripts (`backend/sql/*.sql`), tests (`backend/tests/**/*.py`).
- Key files: `backend/app.py`, `backend/config/supabase.py`, `backend/routes/map.py`, `backend/services/map_pipeline/pipeline.py`, `backend/services/matching/scoring.py`.

**`backend/routes/`:**
- Purpose: Keep one module per API domain with explicit router prefixes/tags.
- Contains: `profile.py`, `interactions.py`, `match.py`, `map.py`, and shared auth dependency in `deps.py`.
- Key files: `backend/routes/profile.py`, `backend/routes/interactions.py`, `backend/routes/match.py`, `backend/routes/map.py`, `backend/routes/deps.py`.

**`backend/services/`:**
- Purpose: Keep non-HTTP business logic and computation modules.
- Contains: `matching/` for profile similarity and `map_pipeline/` for map orchestration and algorithm stages.
- Key files: `backend/services/matching/similarity.py`, `backend/services/matching/scoring.py`, `backend/services/map_pipeline/__init__.py`, `backend/services/map_pipeline/scheduler.py`.

**`backend/sql/`:**
- Purpose: Source-of-truth SQL for schema, RPC functions, triggers, and policy configuration.
- Contains: setup file plus versioned migration scripts.
- Key files: `backend/sql/setup_tables.sql`, `backend/sql/add_increment_interaction_rpc.sql`, `backend/sql/v1.1_phase6_rls_policies.sql`.

**`backend/tests/`:**
- Purpose: Validate route contracts and map pipeline behavior with pytest.
- Contains: endpoint tests (`backend/tests/test_contracts.py`, `backend/tests/test_profile.py`) and map pipeline tests (`backend/tests/map_pipeline/*.py`).
- Key files: `backend/tests/conftest.py`, `backend/tests/test_contracts.py`, `backend/tests/map_pipeline/test_pipeline.py`.

**`frontend/src/`:**
- Purpose: Client application source by concern (bootstrap/router/views/components/lib).
- Contains: root app (`App.vue`), entrypoint (`main.js`), route config (`router/index.js`), feature views, reusable components, Supabase client helper.
- Key files: `frontend/src/main.js`, `frontend/src/router/index.js`, `frontend/src/lib/supabase.js`, `frontend/src/views/Home.vue`, `frontend/src/components/Post.vue`.

**`.planning/codebase/`:**
- Purpose: Persistent architecture/quality/stack maps consumed by GSD planning/execution tools.
- Contains: generated markdown documents such as `ARCHITECTURE.md` and `STRUCTURE.md`.
- Key files: `.planning/codebase/ARCHITECTURE.md`, `.planning/codebase/STRUCTURE.md`.

## Key File Locations

**Entry Points:**
- `backend/app.py`: FastAPI app creation, middleware, router registration, scheduler lifecycle.
- `frontend/src/main.js`: Vue app bootstrap and router mounting.
- `backend/services/map_pipeline/scheduler.py`: Scheduled job registration for periodic pipeline runs.

**Configuration:**
- `backend/config/supabase.py`: Backend Supabase client initialization from environment.
- `backend/config/algorithm.py`: Map/matching algorithm weights and constants.
- `frontend/vite.config.js`: Dev server configuration and `/api` proxy.
- `frontend/src/lib/supabase.js`: Frontend Supabase client configuration and auth helpers.

**Core Logic:**
- `backend/routes/*.py`: HTTP transport and request/response contract handling.
- `backend/services/matching/*.py`: Similarity scoring primitives and matrix composition.
- `backend/services/map_pipeline/*.py`: Map pipeline stages, orchestration, persistence, scheduling.
- `frontend/src/views/*.vue`: Screen-level flows (auth/profile/feed).
- `frontend/src/components/*.vue`: Reusable feed/post UI units.

**Testing:**
- `backend/tests/conftest.py`: Shared fixtures and dependency mocking.
- `backend/tests/test_contracts.py`: API response shape and status code contracts.
- `backend/tests/map_pipeline/*.py`: Algorithm and pipeline behavior tests.

## Naming Conventions

**Files:**
- Python modules use `snake_case.py`: `backend/routes/interactions.py`, `backend/services/map_pipeline/origin_translator.py`.
- Vue SFCs use `PascalCase.vue` for views/components: `frontend/src/views/ProfileSetup.vue`, `frontend/src/components/CreatePost.vue`.
- Frontend JS utility/bootstrap files use lowercase names: `frontend/src/main.js`, `frontend/src/lib/supabase.js`, `frontend/src/router/index.js`.
- SQL migrations use versioned/labeled `snake_case.sql`: `backend/sql/v1.2_phase14_add_timezone_to_profiles.sql`.

**Directories:**
- Backend domain folders are lowercase by concern: `backend/routes/`, `backend/services/matching/`, `backend/services/map_pipeline/`.
- Frontend source grouping uses feature-type folders: `frontend/src/views/`, `frontend/src/components/`, `frontend/src/lib/`, `frontend/src/router/`.

## Where to Add New Code

**New Feature:**
- Primary code: Add backend API handlers in `backend/routes/` and domain logic in `backend/services/` when server-side behavior is required.
- Tests: Add endpoint tests in `backend/tests/` and algorithm/service tests in `backend/tests/map_pipeline/` for pipeline-related logic.

**New Component/Module:**
- Implementation: Add route-level pages to `frontend/src/views/` and reusable UI pieces to `frontend/src/components/`.

**Utilities:**
- Shared helpers: Add backend infrastructure helpers under `backend/config/` or domain-specific helpers near service modules in `backend/services/`; add frontend shared API/client helpers under `frontend/src/lib/`.

## Special Directories

**`backend/venv/`:**
- Purpose: Local Python virtual environment.
- Generated: Yes.
- Committed: No.

**`frontend/node_modules/`:**
- Purpose: Installed npm dependencies.
- Generated: Yes.
- Committed: No.

**`backend/__pycache__/` and nested `__pycache__/`:**
- Purpose: Python bytecode cache.
- Generated: Yes.
- Committed: No.

**`.planning/codebase/`:**
- Purpose: GSD mapping docs used by orchestration commands.
- Generated: Yes.
- Committed: Yes.

---

*Structure analysis: 2026-02-26*
