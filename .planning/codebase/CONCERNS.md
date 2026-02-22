# Codebase Concerns

**Analysis Date:** 2026-02-22

## Critical Blockers

**Authentication Implementation Gap:**
- Issue: Backend auth endpoints (`/auth/login`, `/auth/register`) are completely stubbed in `backend/routes/auth.py`
- Files: `backend/routes/auth.py`, `backend/app.py` (lines 2-3)
- Impact: Backend cannot validate credentials or issue tokens. Frontend bypasses backend entirely and uses Supabase Auth directly, defeating the purpose of having a backend auth layer. This creates a security and architecture mismatch.
- Current state: Frontend auth calls hit Supabase directly; backend routes are never invoked
- Fix approach: Implement POST `/auth/login` and POST `/auth/register` to wrap Supabase Auth operations or use a custom JWT solution

**Database Schema Missing:**
- Issue: Frontend code assumes database tables exist (`posts`, `comments`, `likes`, `profiles`), but these are not created
- Files: `frontend/src/views/Home.vue` (lines 55-58), `frontend/src/components/CreatePost.vue`, `frontend/src/components/Post.vue`
- Impact: Feed is hardcoded with mock data (line 39-50 in Home.vue). Post creation, comments, and likes cannot persist. Feed display shows static test data only.
- Current state: Tables are expected to exist in Supabase; they are not set up via migration system
- Fix approach: Create SQL migrations or use Supabase web UI to define all tables. Add migration system to backend if not present.

**Missing `profiles` Table Relationship:**
- Issue: Posts and comments reference a `profiles` table with `username` field, but schema is undefined
- Files: `frontend/src/components/Post.vue` (lines 7, 52), `frontend/src/components/CreatePost.vue` (line 53)
- Impact: User display names cannot be retrieved. Frontend assumes profiles are linked to posts/comments via foreign key relationships
- Fix approach: Create `profiles` table with user metadata, define relationships in Supabase schema

## Tech Debt

**Frontend Auth Guard Uses localStorage Directly:**
- Issue: Router auth guard checks `localStorage.getItem('supabase_token')` as a string, but Supabase Auth provides session management
- Files: `frontend/src/router/index.js` (line 32)
- Impact: Naive implementation. Token could be expired but still pass the guard. No token refresh logic. Supabase has built-in session management that should be used instead.
- Safe modification: Replace with `supabase.auth.getSession()` call in the guard to check active session validity

**Home.vue Has Broken Function Scope:**
- Issue: `handleLogout()` function (lines 89-93) is nested inside `loadPosts()` function, making it unreachable from template
- Files: `frontend/src/views/Home.vue`
- Impact: The logout button on line 6 will fail at runtime. Function is defined inside async `loadPosts()` but never called
- Fix approach: Move `handleLogout()` outside of `loadPosts()` to module scope

**Unused Dependencies:**
- Issue: Backend requirements include `sqlalchemy`, `psycopg2-binary`, `python-jose`, `passlib` but none are imported or used
- Files: `backend/requirements.txt` (lines 3-6)
- Impact: Increases dependencies without benefit. Suggests incomplete refactoring away from SQLAlchemy/JWT to Supabase-only approach
- Fix approach: Remove unused packages: `sqlalchemy`, `psycopg2-binary`, `python-jose`, `passlib`

**Unused DATABASE_URL Environment Variable:**
- Issue: Backend code never uses `DATABASE_URL` env var; all DB access goes through Supabase client
- Files: CLAUDE.md mentions DATABASE_URL is "optional and currently unused"
- Impact: Leftover from initial setup. Creates confusion about whether direct PostgreSQL connection is needed
- Fix approach: Document that direct DB access is not used; remove DATABASE_URL from .env.example if present

## Security Considerations

**Service Role Key Exposed in Frontend:**
- Issue: Backend uses Supabase service role key (`SUPABASE_KEY`) which is admin credentials
- Files: `backend/config/supabase.py` (line 17), `backend/app.py` - CORS allows any origin via `allow_origins=["http://localhost:5173"]` but no production hardening
- Current mitigation: Localhost only; not suitable for production
- Risk: If key is leaked, attacker has full database access. Hardcoded origins must be environment-driven
- Recommendations:
  - Move CORS config to env vars
  - Use separate read-only Supabase key for some operations
  - Implement proper rate limiting on `/match` endpoints
  - Validate user IDs in match requests match authenticated user

**Frontend Stores Raw JWT in localStorage:**
- Issue: `Login.vue` saves raw token to localStorage without validation
- Files: `frontend/src/views/Login.vue` (line 76)
- Impact: Token is accessible to XSS attacks. No httpOnly cookie alternative
- Recommendations: Use httpOnly cookies for token storage if backend auth is implemented

**No Input Validation on Comments/Posts:**
- Issue: Post and comment content is inserted directly to database with minimal validation
- Files: `frontend/src/components/Post.vue` (lines 193-199), `frontend/src/components/CreatePost.vue` (lines 60-67)
- Impact: Vulnerable to injection attacks if Supabase Row Level Security (RLS) is not configured
- Recommendations: Implement RLS policies on all user-facing tables; sanitize content on display

## Performance Bottlenecks

**In-Memory Distance Matrix Cache:**
- Issue: `/match` routes cache full distance matrix in memory with 5-minute TTL
- Files: `backend/routes/match.py` (lines 17-18, 34-43)
- Problem: As user count grows, similarity matrix is O(N²) in space. With 10k users, this is ~100MB per rebuild. Caching doesn't help if cache invalidates frequently
- Current capacity: Reasonable for < 1000 users
- Scaling path: Move to lazy computation or database-backed cache (Redis); implement cache by user_id instead of full matrix

**PCA Projection Runs on Every Request:**
- Issue: `/graph` endpoint calls `project_to_2d()` which rebuilds similarity matrix and runs PCA every time
- Files: `backend/services/matching/visualization.py` (lines 29-36), `backend/routes/match.py` (lines 90-103)
- Problem: PCA is O(N³) complexity. Even with N=100, this adds latency on every request
- Recommendations: Cache 2D coordinates separately; only rebuild when user profiles change

**Jaccard Similarity Uses Set Operations on Every Pair:**
- Issue: `similarity.py` calls `set(a) & set(b)` for every field pair comparison
- Files: `backend/services/matching/similarity.py` (lines 84-95)
- Problem: Repeated list-to-set conversions are wasteful. For interests/languages, could pre-compute sets
- Fix approach: Pre-compute sets during user fetch; pass sets to similarity functions

## Fragile Areas

**Matching Algorithm Depends on Field Order:**
- Issue: `FEATURE_COLS` list order (line 26 in `scoring.py`) must match weight order in `DEFAULT_WEIGHTS` dict
- Files: `backend/services/matching/scoring.py` (lines 26, 68)
- Why fragile: Python dicts maintain insertion order (3.7+) but this is fragile. Reordering either breaks the algorithm silently
- Safe modification: Use explicit column mapping instead of relying on dict order (e.g., `{field: (idx, weight)}`)
- Test coverage: No tests exist to catch this if order changes

**Category Mappings Are Hardcoded Enums:**
- Issue: `FIELD_OF_STUDY_CATEGORIES` and `INDUSTRY_CATEGORIES` are Python dicts in `similarity.py`
- Files: `backend/services/matching/similarity.py` (lines 7-81)
- Why fragile: Adding new field values requires code change + backend redeploy. Should be database-driven
- Safe modification: Move categories to Supabase table; load at startup or cache
- Test coverage: No tests validate that all profile fields are covered

**User ID Lookup is O(N):**
- Issue: `clustering.py` builds dict from users list on every request
- Files: `backend/services/matching/clustering.py` (line 35)
- Why fragile: If user ID format changes (UUID vs string), no validation catches it. Silent failure on mismatch
- Safe modification: Add explicit user ID validation; use set for O(1) lookup if list is large

**Home.vue Assumes Profile Structure:**
- Issue: Home.vue hardcodes post object shape with `tier`, `profiles.username`, `like_count`, `comment_count`
- Files: `frontend/src/views/Home.vue` (lines 40-50)
- Why fragile: If database schema changes (rename field, restructure), component breaks silently
- Safe modification: Use TypeScript or JSDoc to define Post type; add runtime schema validation
- Test coverage: No tests for component rendering with different data shapes

## Test Coverage Gaps

**No Tests for Matching Algorithm:**
- What's not tested: Similarity scoring, distance matrix construction, KNN clustering, tier assignment
- Files: `backend/services/matching/` (all files)
- Risk: Algorithm could silently break during refactoring. Weight changes go unchecked. Edge cases like 0 users, 1 user, identical profiles not validated
- Priority: High (core feature)
- Recommendation: Add pytest suite for similarity, scoring, clustering with fixtures for known user pairs

**No Tests for API Endpoints:**
- What's not tested: `/match/users/{user_id}/matches`, `/match/graph`, `/match/invalidate-cache`
- Files: `backend/routes/match.py`
- Risk: HTTP status codes, error handling, edge cases (missing user, empty user list, invalid params) not validated
- Priority: High
- Recommendation: Add FastAPI TestClient tests for all routes

**No Tests for Frontend Components:**
- What's not tested: Post rendering, CreatePost form, comment flow, like button, auth guard
- Files: `frontend/src/components/`, `frontend/src/views/`
- Risk: UI could break without notice. Components fail when Supabase schema changes
- Priority: Medium
- Recommendation: Add Vue test utils + vitest suite

**No Tests for Auth Flow:**
- What's not tested: Login, signup, token storage, session persistence, logout
- Files: `frontend/src/views/Login.vue`, `frontend/src/views/SignUp.vue`, `frontend/src/router/index.js`
- Risk: Auth bypass or token leakage not caught. Router guard logic unchecked
- Priority: Critical
- Recommendation: Add integration tests for full auth flow with mocked Supabase

## Missing Critical Features

**Profile Creation Page:**
- Problem: No UI to collect initial user profile data (interests, location, education, industry, etc.)
- Blocks: Matching algorithm cannot run without UserProfile objects
- Current state: Profiles must be created via Supabase web UI or direct API
- Impact: Users cannot onboard naturally

**Matching Results Display:**
- Problem: No frontend page to display match results from `/match/users/{user_id}/matches` endpoint
- Blocks: Users cannot see who they match with or their tier ranking
- Current state: Endpoint exists but is never called by frontend
- Impact: Core feature (showing matches) is unavailable

**Social Graph Visualization:**
- Problem: `/match/graph` endpoint returns 2D coordinates but no frontend component uses them
- Blocks: Cannot display the visual network graph
- Current state: Endpoint exists but is never called
- Impact: "Social graph" display feature is incomplete

## Scaling Limits

**User Count:**
- Current capacity: ~1000 users before matching becomes slow (O(N²) similarity matrix)
- Limit: Cache rebuild becomes expensive; PCA projection slows down
- Scaling path: Implement approximate KNN (locality-sensitive hashing); cache by user ID instead of full matrix

**Database Queries:**
- Current: No query optimization. Fetches all users every 5 minutes
- Limit: Scales with N. If 100k users, loading all profiles becomes bottleneck
- Scaling path: Add pagination; implement incremental updates (only recalculate for changed users)

**Real-Time Features:**
- Current: No real-time post feed, no subscriptions, polling-based
- Scaling path: Add Supabase real-time subscriptions for posts/comments/likes

## Dependencies at Risk

**Supabase Service Role Key as Single Source of Truth:**
- Risk: Backend depends entirely on Supabase. If Supabase is down, all APIs fail
- Impact: No fallback; no caching layer
- Migration plan: None currently. Consider adding Redis cache or implementing offline-first patterns

**NumPy/Scikit-Learn Version Pinning:**
- Risk: No exact version pinning. `numpy>=1.26` and `scikit-learn>=1.4` could introduce breaking changes
- Impact: Reproducibility issues across environments
- Recommendation: Pin exact versions in requirements.txt (e.g., `numpy==1.26.0`)

**Vite + Vue 3 Rapidly Evolving:**
- Risk: Frontend depends on cutting-edge frameworks. No lock on exact versions
- Impact: `npm install` could pull incompatible versions
- Recommendation: Use package-lock.json or pnpm-lock.yaml; pin major versions tighter (e.g., `^3.4.0` instead of `^3`)

## Database Schema Issues

**Missing Foreign Key Relationships:**
- Issue: `posts`, `comments`, `likes` tables are not defined; relationship to `users`/`profiles` is unknown
- Files: Not in codebase (created in Supabase web UI)
- Impact: No constraints. Orphaned records possible. No cascading deletes
- Fix approach: Define explicit foreign keys; add CASCADE DELETE rules

**No Timestamps or Soft Deletes:**
- Issue: Created/updated timestamps not mentioned in code; deletion is likely hard delete
- Files: Frontend assumes `created_at` on posts (Home.vue, CreatePost.vue)
- Impact: Cannot audit history; cannot implement soft delete
- Recommendation: Add `created_at`, `updated_at`, `deleted_at` to all tables

**Tier Field Not Normalized:**
- Issue: `posts.tier` stores values like `inner_circle`, `2nd_degree`, `3rd_degree` as strings
- Files: `frontend/src/components/CreatePost.vue` (lines 14-18)
- Impact: Typos possible; no enum constraint; inconsistent naming
- Recommendation: Create `tiers` table with enum values; use foreign key reference

---

*Concerns audit: 2026-02-22*
