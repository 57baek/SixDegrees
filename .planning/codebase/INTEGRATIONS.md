# External Integrations

**Analysis Date:** 2026-02-26

## APIs & External Services

**Backend-as-API (internal app API):**
- FastAPI service - authenticated endpoints for profile/interactions/match/map
  - SDK/Client: FastAPI server in `backend/app.py`; no dedicated frontend REST client currently in `frontend/src/`
  - Auth: Bearer token validated through Supabase auth in `backend/routes/deps.py`

**Supabase Platform:**
- Supabase Postgres + RPC functions - primary data plane for both backend and frontend
  - SDK/Client: Python `supabase` client in `backend/config/supabase.py`; JS `@supabase/supabase-js` in `frontend/src/lib/supabase.js`
  - Auth: Backend uses `SUPABASE_URL` + `SUPABASE_KEY` in `backend/config/supabase.py`; frontend uses `VITE_SUPABASE_URL` + `VITE_SUPABASE_ANON_KEY` in `frontend/src/lib/supabase.js`

**Supabase Auth (JWT identity):**
- User signup/login/session - frontend calls `supabase.auth.*`, backend validates JWT with `sb.auth.get_user(token)`
  - SDK/Client: `@supabase/supabase-js` in `frontend/src/views/Login.vue`, `frontend/src/views/SignUp.vue`; Python supabase auth access in `backend/routes/deps.py`
  - Auth: JWT bearer token stored in `localStorage` key `supabase_token` in `frontend/src/router/index.js` and `frontend/src/views/Login.vue`

## Data Storage

**Databases:**
- Supabase Postgres
  - Connection: `SUPABASE_URL` and `SUPABASE_KEY` in `backend/config/supabase.py`
  - Client: Python Supabase client in `backend/config/supabase.py`; JS Supabase client in `frontend/src/lib/supabase.js`
  - Schema/RLS/function definitions in `backend/sql/setup_tables.sql`, `backend/sql/v1.1_phase6_rls_policies.sql`, `backend/sql/add_increment_interaction_rpc.sql`

**File Storage:**
- Not detected (no Supabase Storage SDK usage or storage bucket operations found in `backend/` or `frontend/src/`)

**Caching:**
- None detected (no Redis/Memcached/service cache client imports found)

## Authentication & Identity

**Auth Provider:**
- Supabase Auth
  - Implementation: Frontend performs `signUp`/`signInWithPassword` and session handling in `frontend/src/views/SignUp.vue` and `frontend/src/views/Login.vue`; backend enforces auth via `Depends(get_current_user)` in `backend/routes/deps.py` and route files under `backend/routes/`

## Monitoring & Observability

**Error Tracking:**
- None detected (no Sentry/Bugsnag/Rollbar SDK usage found)

**Logs:**
- Backend uses Python logging in scheduler (`backend/services/map_pipeline/scheduler.py`)
- Backend/frontend also use `print`/`console.error` in operational flows (`backend/scripts/seed_db.py`, `frontend/src/views/*.vue`, `frontend/src/components/*.vue`)

## CI/CD & Deployment

**Hosting:**
- Not explicitly declared (no platform config files detected)
- Current dev topology: frontend Vite on `5173` and backend FastAPI on `8000` with Vite proxy in `frontend/vite.config.js`

**CI Pipeline:**
- None detected (no `.github/workflows/*.yml` or `.github/workflows/*.yaml`)

## Environment Configuration

**Required env vars:**
- Backend: `SUPABASE_URL`, `SUPABASE_KEY` from `backend/config/supabase.py` and `AGENTS.md`
- Frontend: `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY` from `frontend/src/lib/supabase.js` and `AGENTS.md`

**Secrets location:**
- Local env files present at `backend/.env` and `frontend/.env` (contents not inspected)
- Template env files present at `backend/.env.example` and `frontend/.env.example` (contents not inspected)

## Webhooks & Callbacks

**Incoming:**
- None detected (no webhook endpoints or callback handler routes found in `backend/routes/`)

**Outgoing:**
- None detected (no outbound webhook publishers or third-party callback registrations found)

---

*Integration audit: 2026-02-26*
