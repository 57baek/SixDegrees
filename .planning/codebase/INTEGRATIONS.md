# External Integrations

**Analysis Date:** 2026-02-22

## APIs & External Services

**Supabase (Primary):**
- Supabase Platform - Backend-as-a-service providing PostgreSQL, authentication, and real-time APIs
  - SDK/Client: `@supabase/supabase-js` (frontend, v2.94.0), `supabase` Python package (backend)
  - Auth: Frontend uses `VITE_SUPABASE_ANON_KEY` (anon/public key), Backend uses `SUPABASE_KEY` (service role key for admin operations)
  - Usage: Authentication, user profile data, posts, likes, comments, real-time subscriptions
  - Location: Frontend client initialized in `frontend/src/lib/supabase.js`, Backend client in `backend/config/supabase.py`

## Data Storage

**Databases:**
- Supabase PostgreSQL (managed cloud database)
  - Connection: `SUPABASE_URL` + `SUPABASE_KEY` (backend) or `VITE_SUPABASE_URL` + `VITE_SUPABASE_ANON_KEY` (frontend)
  - Client: Supabase JS client (frontend), Supabase Python client (backend)
  - Tables expected: `users` (with UserProfile fields), `posts`, `likes`, `comments`, `profiles`
  - Status: Tables created in Supabase web UI; no migration system in place
  - ORM: SQLAlchemy (2.0.25) imported in requirements.txt but not yet actively used; Supabase client is used instead

**File Storage:**
- Not configured. No S3, GCS, or Supabase Storage integration detected.

**Caching:**
- In-memory cache only. Backend match endpoint uses 5-minute TTL cache for distance matrix (`backend/routes/match.py`, lines 17-18)
- No Redis or external caching service

## Authentication & Identity

**Auth Provider:**
- Supabase Auth (built into Supabase)
  - Implementation: Frontend calls Supabase Auth API directly; backend does not provide auth endpoints
  - Auth flow: Email/password via Supabase JS client (`frontend/src/lib/supabase.js`)
  - Token storage: localStorage `supabase_token` (frontend) and `user_id` (frontend)
  - Routes: Backend auth stubs exist (`backend/routes/auth.py`) but `/auth/login` and `/auth/register` are not implemented
  - Guard: Vue Router auth guard checks localStorage token before allowing protected route access

**JWT Tokens:**
- Supabase Auth provides JWT tokens automatically
- python-jose[cryptography] (3.3.0) is in requirements for future backend JWT validation but not yet used

**Password Handling:**
- Supabase Auth handles password hashing; frontend never sees raw passwords
- passlib[bcrypt] (1.7.4) is in requirements for future backend password hashing but not yet used

## Monitoring & Observability

**Error Tracking:**
- Not detected. No Sentry, DataDog, or similar error tracking service configured.

**Logs:**
- Console logging only. No structured logging framework detected.
- FastAPI logs to stdout via uvicorn

## CI/CD & Deployment

**Hosting:**
- Frontend: Not yet deployed (development only on localhost:5173)
- Backend: Not yet deployed (development only on localhost:8000 via uvicorn --reload)
- Infrastructure: Supabase handles PostgreSQL hosting

**CI Pipeline:**
- Not configured. No GitHub Actions, GitLab CI, or other CI/CD service detected.

## Environment Configuration

**Required env vars:**

**Frontend (.env):**
- `VITE_SUPABASE_URL` - Supabase project URL (e.g., https://your-project-id.supabase.co)
- `VITE_SUPABASE_ANON_KEY` - Supabase public/anon key (safe for frontend)

**Backend (.env):**
- `SUPABASE_URL` - Supabase project URL
- `SUPABASE_KEY` - Supabase service role key (admin, keep secret)
- `DATABASE_URL` - (Optional) PostgreSQL connection string; currently unused

**Secrets location:**
- `.env` files in frontend/ and backend/ directories (local development only)
- `.env` files listed in `.gitignore` and should never be committed
- Production: Environment variables must be set in deployment platform (e.g., Vercel, Railway, render.com)

## Webhooks & Callbacks

**Incoming:**
- None detected. No webhook endpoints for external services.

**Outgoing:**
- None detected. No outgoing webhooks to external services.

## API Usage

**Frontend to Backend:**
- Vite proxy routes `/api/*` requests to `http://localhost:8000` (configured in `frontend/vite.config.js`)
- Axios client used for HTTP calls (`frontend/src/`)
- Active endpoints: `/match/users/{user_id}/matches`, `/match/graph`, `/match/invalidate-cache`
- Direct Supabase calls for auth and database operations bypass backend

**Backend to Supabase:**
- Supabase client (`config/supabase.py`) used for database queries
- Service role key grants admin access to `users` table
- No custom Supabase functions or stored procedures detected

---

*Integration audit: 2026-02-22*
