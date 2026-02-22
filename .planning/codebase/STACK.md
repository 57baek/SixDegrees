# Technology Stack

**Analysis Date:** 2026-02-22

## Languages

**Primary:**
- JavaScript (ES6+) - Frontend application (`frontend/src/`)
- Python 3.9+ - Backend API and matching algorithm (`backend/`)
- SQL (PostgreSQL) - Database queries via Supabase

**Secondary:**
- Vue 3 template syntax (SFC) - UI components (`frontend/src/components/`, `frontend/src/views/`)

## Runtime

**Environment:**
- Node.js (implied by package.json type: "module" and npm usage)
- Python 3.9+ (standard for FastAPI/uvicorn)

**Package Manager:**
- Frontend: npm (with package-lock.json present)
- Backend: pip (with requirements.txt)
- Lockfiles: Both package-lock.json and requirements-installed tracking present

## Frameworks

**Core:**
- Vue 3 (^3.4.0) - Frontend SPA framework (`frontend/src/`)
- FastAPI (0.109.0) - Python async web framework and REST API (`backend/app.py`, `backend/routes/`)
- Vite (^5.0.0) - Frontend build tool and dev server (`frontend/vite.config.js`)

**Frontend Routing:**
- Vue Router (^5.0.2) - Client-side routing with auth guards (`frontend/src/router/`)

**Testing:**
- No testing framework currently configured (no jest.config, vitest.config, pytest.ini detected)

**Build/Dev:**
- @vitejs/plugin-vue (^5.0.0) - Vite plugin for Vue SFC support
- Vite (^5.0.0) - Dev server on port 5173 with API proxy to backend on port 8000

## Key Dependencies

**Critical:**
- @supabase/supabase-js (^2.94.0) - Frontend auth and database client (`frontend/src/lib/supabase.js`)
- supabase (Python) - Backend admin client via service role key (`backend/config/supabase.py`)
- FastAPI (0.109.0) - Core backend framework (`backend/app.py`)
- uvicorn[standard] (0.27.0) - ASGI server for FastAPI on port 8000
- pydantic - Data validation and serialization for API models (`backend/models/user.py`)
- sqlalchemy (2.0.25) - ORM (imported in requirements but not yet actively used)

**Infrastructure:**
- psycopg2-binary (2.9.9) - PostgreSQL database adapter
- python-dotenv (1.0.0) - Environment variable loading (`backend/config/supabase.py`)
- python-jose[cryptography] (3.3.0) - JWT token handling (for future auth implementation)
- passlib[bcrypt] (1.7.4) - Password hashing (for future auth implementation)

**Data Science/Matching Algorithm:**
- numpy (>=1.26) - Numerical computations for similarity matrices (`backend/services/matching/`)
- scikit-learn (>=1.4) - Machine learning utilities; used for PCA dimensionality reduction (`backend/services/matching/visualization.py`)

**Frontend UI:**
- axios (^1.6.0) - HTTP client for API calls (`frontend/src/`)
- lucide-vue-next (^0.574.0) - Vue icon library for UI components

## Configuration

**Environment:**
- Frontend env vars loaded from `.env` file with VITE_ prefix:
  - `VITE_SUPABASE_URL` - Supabase project URL
  - `VITE_SUPABASE_ANON_KEY` - Supabase public/anon key for frontend auth
- Backend env vars loaded from `.env` file via python-dotenv:
  - `SUPABASE_URL` - Supabase project URL
  - `SUPABASE_KEY` - Supabase service role key (admin access)
  - `DATABASE_URL` - Optional PostgreSQL connection string (currently unused)
- `.env.example` files provided in both frontend and backend directories

**Build:**
- Vite config: `frontend/vite.config.js` - Configures dev server port 5173, API proxy to backend, Vue plugin
- FastAPI CORS config: `backend/app.py` - Allows origin `http://localhost:5173`

## Platform Requirements

**Development:**
- Node.js with npm (frontend)
- Python 3.9+ with pip (backend)
- Supabase account with project credentials
- Vite dev server: port 5173
- FastAPI dev server: port 8000

**Production:**
- Node.js runtime for frontend (can be served via CDN or static host)
- Python 3.9+ runtime for backend FastAPI
- Supabase PostgreSQL database (cloud-hosted)
- Environment variables for Supabase credentials must be configured at deployment

---

*Stack analysis: 2026-02-22*
