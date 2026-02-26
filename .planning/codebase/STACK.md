# Technology Stack

**Analysis Date:** 2026-02-26

## Languages

**Primary:**
- Python - Backend API, scheduler, and map/matching pipeline in `backend/app.py`, `backend/routes/*.py`, `backend/services/**/*.py`
- JavaScript (ES modules) - Frontend SPA in `frontend/src/**/*.js` and `frontend/src/**/*.vue`

**Secondary:**
- SQL (PostgreSQL dialect) - Database schema/RLS/functions in `backend/sql/setup_tables.sql`, `backend/sql/v1.1_phase6_rls_policies.sql`, `backend/sql/add_increment_interaction_rpc.sql`
- Markdown - Operational docs in `AGENTS.md`

## Runtime

**Environment:**
- Python 3 (exact version not pinned) - inferred from `python3` setup/run commands in `AGENTS.md`
- Node.js (exact version not pinned) - implied by `vite`/`npm` scripts in `frontend/package.json`

**Package Manager:**
- npm (frontend) - scripts and deps in `frontend/package.json`
- pip (backend) - dependency file `backend/requirements.txt`
- Lockfile: frontend present (`frontend/package-lock.json`), backend lockfile not detected

## Frameworks

**Core:**
- FastAPI `0.109.0` - HTTP API and routing in `backend/requirements.txt` and `backend/app.py`
- Vue `^3.4.0` - frontend UI framework in `frontend/package.json` and `frontend/src/main.js`
- Vue Router `^5.0.2` - client routing/auth guard in `frontend/package.json` and `frontend/src/router/index.js`

**Testing:**
- pytest `>=8.0` - backend test runner in `backend/requirements.txt` with tests in `backend/tests/`
- Starlette TestClient (via FastAPI/Starlette) - API tests in `backend/tests/conftest.py`
- httpx `>=0.27` - backend test dependency in `backend/requirements.txt`

**Build/Dev:**
- Vite `^5.0.0` - frontend dev/build in `frontend/package.json` and `frontend/vite.config.js`
- `@vitejs/plugin-vue` `^5.0.0` - Vue support in Vite from `frontend/package.json` and `frontend/vite.config.js`
- Uvicorn `0.27.0` (`uvicorn[standard]`) - backend ASGI server in `backend/requirements.txt` and run command in `AGENTS.md`
- APScheduler `>=3.10,<4` - in-process scheduled jobs in `backend/requirements.txt` and `backend/services/map_pipeline/scheduler.py`

## Key Dependencies

**Critical:**
- `supabase` (version not pinned) - backend Supabase client creation/usage in `backend/config/supabase.py` and `backend/routes/*.py`
- `@supabase/supabase-js` `^2.94.0` - frontend auth/data/RPC client in `frontend/src/lib/supabase.js` and `frontend/src/views/*.vue`
- `pydantic` (version not pinned) - request/data models in `backend/routes/profile.py` and `backend/models/user.py`
- `numpy>=1.26` - numeric matrix processing in `backend/services/matching/scoring.py` and `backend/services/map_pipeline/*.py`
- `scikit-learn>=1.4` - t-SNE projection via `sklearn.manifold.TSNE` in `backend/services/map_pipeline/tsne_projector.py`

**Infrastructure:**
- `python-dotenv==1.0.0` - backend env loading in `backend/config/supabase.py`
- `lucide-vue-next` `^0.574.0` - frontend icons in `frontend/src/components/Post.vue`
- `axios` `^1.6.0` - listed in `frontend/package.json` (usage not detected under `frontend/src/`)
- `matplotlib>=3.10`, `jupyter`, `ipykernel==6.30.1` - demo/notebook tooling in `backend/requirements.txt`

## Configuration

**Environment:**
- Backend env vars are loaded with `load_dotenv()` and `os.getenv()` in `backend/config/supabase.py`
- Frontend env vars use Vite `import.meta.env` in `frontend/src/lib/supabase.js`
- Required backend vars: `SUPABASE_URL`, `SUPABASE_KEY` (documented in `AGENTS.md`, enforced in `backend/config/supabase.py`)
- Required frontend vars: `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY` (documented in `AGENTS.md`, enforced in `frontend/src/lib/supabase.js`)
- `.env` files are present at `backend/.env` and `frontend/.env` (contents not inspected)

**Build:**
- Frontend build/dev config in `frontend/vite.config.js` (dev server port `5173`, `/api` proxy to `http://localhost:8000`)
- Backend app/lifespan/CORS setup in `backend/app.py`
- No root build orchestrator file detected; commands are app-local per `AGENTS.md`

## Platform Requirements

**Development:**
- Backend: Python virtualenv + pip install from `backend/requirements.txt`; run with `uvicorn app:app --reload` from `backend/` (`AGENTS.md`)
- Frontend: npm install from `frontend/package.json`; run with `npm run dev` from `frontend/` (`frontend/package.json`, `AGENTS.md`)
- Backend should run single worker because APScheduler is in-process (`backend/app.py`, `backend/services/map_pipeline/scheduler.py`)

**Production:**
- Deployment platform is not explicitly configured (no `.github/workflows/*`, `Dockerfile*`, `vercel.json`, `netlify.toml`, or `render.yaml` detected)
- Architecture indicates Supabase-hosted Postgres/Auth + self-hosted FastAPI + static/frontend host to be decided (`backend/config/supabase.py`, `frontend/src/lib/supabase.js`)

---

*Stack analysis: 2026-02-26*
