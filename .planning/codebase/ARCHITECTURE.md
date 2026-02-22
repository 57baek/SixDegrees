# Architecture

**Analysis Date:** 2026-02-22

## Pattern Overview

**Overall:** Layered client-server architecture with algorithmic backend and reactive frontend.

**Key Characteristics:**
- Frontend: Vue 3 + Vite SPA with Supabase Auth integrated directly on client
- Backend: FastAPI service focused on matching algorithm computation (read-only for users table)
- Matching: Multi-stage pipeline transforming user similarity scores into tiered KNN rankings
- State: Frontend uses Supabase Auth tokens in localStorage; backend uses 5-min in-memory cache for distance matrix
- Communication: REST API with CORS configured for local dev

## Layers

**Frontend Presentation (`frontend/src/views/`, `frontend/src/components/`):**
- Purpose: Render user interface and handle user interactions
- Location: `frontend/src/`
- Contains: Vue 3 components (.vue files), router configuration, Supabase client initialization
- Depends on: Supabase JS SDK, Vue Router, lucide-vue-next icons
- Used by: End users via browser

**Frontend Routing & Auth Guard (`frontend/src/router/index.js`):**
- Purpose: Control page access and redirect unauthenticated users
- Location: `frontend/src/router/index.js`
- Contains: Route definitions, navigation guard checking `localStorage.supabase_token`
- Depends on: Vue Router, localStorage API
- Used by: App.vue to render correct view

**Frontend Supabase Integration (`frontend/src/lib/supabase.js`):**
- Purpose: Initialize Supabase client and expose auth helper functions
- Location: `frontend/src/lib/supabase.js`
- Contains: Client configuration, `isAuthenticated()`, `getCurrentUser()`, `signOut()` helpers
- Depends on: @supabase/supabase-js
- Used by: All views and components for auth and database operations

**Backend HTTP Layer (`backend/app.py`):**
- Purpose: FastAPI application setup, CORS middleware, router mounting
- Location: `backend/app.py`
- Contains: FastAPI app initialization, CORS configuration for localhost:5173, router includes
- Depends on: FastAPI, CORSMiddleware
- Used by: Uvicorn ASGI server (entry point)

**Backend Route Handlers (`backend/routes/`):**
- Purpose: HTTP endpoint implementations
- Location: `backend/routes/`
- Contains: APIRouter instances defining `/match` and `/auth` endpoints
- Depends on: Models, services, Supabase config
- Used by: FastAPI app router mounting

**Backend Data Models (`backend/models/user.py`):**
- Purpose: Define request/response schemas
- Location: `backend/models/user.py`
- Contains: `UserProfile` (Pydantic model with user attributes), `MatchResult` (user + score + tier)
- Depends on: Pydantic
- Used by: Routes for validation and serialization

**Backend Configuration (`backend/config/supabase.py`):**
- Purpose: Manage Supabase client initialization and environment validation
- Location: `backend/config/supabase.py`
- Contains: Supabase client creation with service role key, `get_supabase_client()` function
- Depends on: supabase Python SDK, python-dotenv
- Used by: Routes to fetch data from database

**Backend Matching Services (`backend/services/matching/`):**
- Purpose: Compute user similarity, scoring, clustering, and visualization
- Location: `backend/services/matching/`
- Contains: Four specialized modules (similarity.py, scoring.py, clustering.py, visualization.py)
- Depends on: NumPy, scikit-learn (PCA), Pydantic models
- Used by: `routes/match.py`

## Data Flow

**User Matches Query (`GET /match/users/{user_id}/matches`):**

1. Client calls `/match/users/user123/matches` with optional k1, k2, max_distance query params
2. `routes/match.py` calls `_get_cached_data()` to retrieve users and distance matrix
3. If cache is stale (>5 min old), `_fetch_all_users()` queries Supabase `users` table
4. `build_similarity_matrix()` computes per-field similarity scores for all user pairs
5. `apply_weights()` combines per-field scores using DEFAULT_WEIGHTS (interests 35%, location 20%, etc.)
6. `similarity_to_distance()` converts scores to distances (distance = 1 - similarity)
7. `get_ranked_matches()` sorts target user's distances, assigns tier labels (tier 1: k1 closest, tier 2: next k2-k1, tier 3: rest within max_distance)
8. Returns list of MatchResult objects (user + similarity score + tier)
9. Client receives JSON response and renders in matching/discovery UI

**Social Graph Query (`GET /match/graph`):**

1. Client calls `/match/graph` to fetch 2D coordinates for visualization
2. Route retrieves cached users and distance matrix
3. `project_to_2d()` builds weighted similarity matrix and applies PCA(n_components=2)
4. Returns array of {id, x, y} coordinates normalized by PCA
5. Frontend renders as interactive graph with users positioned by similarity clustering

**Post Creation Flow (Frontend → Supabase, not backend):**

1. User types in CreatePost.vue textarea
2. Clicks "Post" button
3. `handlePost()` calls `supabase.auth.getUser()` to verify authentication
4. Inserts row into `posts` table with user_id, content, tier, created_at
5. Emits 'post-created' event to parent (Home.vue)
6. Home.vue fetches posts (currently uses mock data)

**State Management:**

- **Frontend auth state:** `localStorage.supabase_token` (manually persisted) and Supabase session (auto-refreshed)
- **Backend matching state:** In-memory cache dict `_cache` with keys: "users", "matrix", "timestamp"; invalidated on POST `/match/invalidate-cache` or after 5-minute TTL
- **Post/feed state:** Mock data in Home.vue (TODO: switch to Supabase query once tables exist)

## Key Abstractions

**UserProfile:**
- Purpose: Represents a user's immutable profile attributes (interests, location, education, etc.)
- Examples: `backend/models/user.py:4-14`
- Pattern: Pydantic BaseModel with type annotations; used as both Supabase row schema and API response type

**Similarity Functions (Pure Functions):**
- Purpose: Compute [0,1] similarity scores for individual fields
- Examples: `jaccard()`, `tiered_location()`, `tiered_categorical()`, `binary_match()`, `inverse_distance_age()` in `backend/services/matching/similarity.py`
- Pattern: Each function is pure (no I/O), takes two values, returns float in [0,1]; composed into `_similarity_vector()`

**Similarity Matrix (NumPy N×N×F):**
- Purpose: Store per-field similarity scores for all user pairs in compact form
- Pattern: 3D array where `sim_matrix[i][j]` is a vector of F feature similarities between users i and j
- Usage: Intermediate representation built once per cache cycle, then weighted and converted to distance

**Tiered KNN Ranking:**
- Purpose: Classify matches into inner circle (tier 1), second degree (tier 2), third degree (tier 3)
- Examples: `backend/services/matching/clustering.py:13-70`
- Pattern: Sort distances for target user, assign tier based on rank thresholds (k1, k2); filter by max_distance

**Vue Router Auth Guard:**
- Purpose: Prevent navigation to protected routes without authentication
- Examples: `frontend/src/router/index.js:31-40`
- Pattern: `router.beforeEach()` checks `localStorage.getItem('supabase_token')` before allowing navigation to routes with `meta: { requiresAuth: true }`

## Entry Points

**Frontend Application:**
- Location: `frontend/src/main.js`
- Triggers: `npm run dev` (Vite) or browser opens http://localhost:5173
- Responsibilities: Mount Vue app, initialize router, log Supabase connection status

**Backend API:**
- Location: `backend/app.py`
- Triggers: `uvicorn app:app --reload` or production container startup
- Responsibilities: Configure CORS, mount routers, serve HTTP endpoints

**Matching Routes:**
- Location: `backend/routes/match.py`
- Endpoints:
  - `GET /match/users/{user_id}/matches` - Fetch ranked matches for a user
  - `GET /match/graph` - Fetch 2D PCA coordinates for all users
  - `POST /match/invalidate-cache` - Force cache rebuild

**Auth Routes (Stub):**
- Location: `backend/routes/auth.py`
- Status: Not implemented; TODO routes listed as comments
- Note: Frontend currently bypasses backend for auth, calling Supabase directly

## Error Handling

**Strategy:** Backend returns HTTP 404 for missing users; frontend displays Supabase error messages; no global error boundary yet.

**Patterns:**

- **Backend 404s:** `routes/match.py` line 76-77 raises `HTTPException(status_code=404)` if user_id not found
- **Supabase Errors:** Frontend catches `supabaseError` from auth/database operations, displays in UI (e.g., Login.vue line 71, CreatePost.vue line 80)
- **Frontend Validation:** CreatePost.vue disables submit button if content is empty; SignUp.vue shows real-time password validation checklist
- **Cache Invalidation:** POST `/match/invalidate-cache` resets timestamp to force immediate rebuild on next query

## Cross-Cutting Concerns

**Logging:**
- Backend: None; TODO comments mark stubs
- Frontend: `console.log()` for Supabase connection debug (main.js line 13-15), error logs in components

**Validation:**
- Frontend: Pydantic BaseModel for UserProfile and MatchResult; password validation checklist in SignUp.vue
- Form inputs: HTML5 `required` attributes, Vue `v-model` two-way binding

**Authentication:**
- Mechanism: Supabase Auth (email/password)
- Token storage: `localStorage.supabase_token` (frontend manually sets; Supabase auto-refreshes session)
- Route protection: Router guard checks localStorage token before allowing access to `/` (Home.vue)
- Backend routes: No authentication check; routes trust frontend has validated user (TODO: add backend auth)

---

*Architecture analysis: 2026-02-22*
