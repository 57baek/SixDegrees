# Codebase Concerns

**Analysis Date:** 2026-02-26

## Tech Debt

**Schema naming drift (profiles vs user_profiles):**
- Issue: Application code targets `profiles` while foundational SQL and RLS scripts target `user_profiles`, creating dual-schema assumptions in one codebase.
- Files: `backend/scripts/seed_db.py`, `frontend/src/views/Login.vue`, `frontend/src/views/Profile.vue`, `frontend/src/views/ProfileSetup.vue`, `frontend/src/views/SignUp.vue`, `backend/sql/setup_tables.sql`, `backend/sql/v1.1_phase6_rls_policies.sql`, `backend/sql/v1.1_phase13_fk_repair.sql`, `backend/sql/v1.2_phase14_add_timezone_to_profiles.sql`
- Impact: Migrations and runtime behavior can diverge by environment, causing missing columns/RPC failures, broken joins, and hard-to-reproduce onboarding or profile issues.
- Fix approach: Standardize on one canonical table name, add one migration that aligns schema + FKs + RLS + RPCs, and update all `.from(...)` and SQL references to that canonical name.

**Frontend business logic embedded in large views:**
- Issue: Core product flows (friend requests, feed loading, profile editing) are implemented directly inside oversized Vue SFCs with mixed UI/network logic.
- Files: `frontend/src/views/Profile.vue`, `frontend/src/views/Home.vue`, `frontend/src/views/SignUp.vue`, `frontend/src/components/Post.vue`
- Impact: High change risk, hard debugging, and frequent regressions when modifying unrelated UI sections.
- Fix approach: Extract API composables (`useProfile`, `useFeed`, `useFriends`), keep components presentation-focused, and centralize Supabase RPC handling + error mapping.

## Known Bugs

**Unlike action sends wrong post identifier:**
- Symptoms: Clicking unlike does not remove the like count correctly (or calls RPC with null/undefined ID).
- Files: `frontend/src/components/Post.vue`
- Trigger: In `handleLike`, unlike branch calls `supabase.rpc('unlike_post', { liked_post_id: props.post_id })` instead of `props.post.id`.
- Workaround: None in UI; users can only recover by reloading and trying again after data correction.

**Profile page links to a non-existent route:**
- Symptoms: Clicking "Friends" from profile navigates to a route that is not registered.
- Files: `frontend/src/views/Profile.vue`, `frontend/src/router/index.js`
- Trigger: `router.push('/friends')` is used, but `/friends` is absent from router route definitions.
- Workaround: Navigate back to `/` manually.

**Nickname validation path is broken/inconsistent:**
- Symptoms: Signup nickname availability indicator behaves unpredictably or reports wrong availability.
- Files: `frontend/src/views/SignUp.vue`
- Trigger: Blur handler assigns `showValidation = ~uniqueUser` (bitwise NOT on a ref), and query filters on `.eq('lowercase', nick)` which does not map to any verified column in app code.
- Workaround: Users can proceed by trial-and-error until signup succeeds.

## Security Considerations

**Map read endpoint does not enforce self-access:**
- Risk: Any authenticated user can request another user's map payload by ID.
- Files: `backend/routes/map.py`
- Current mitigation: Endpoint requires JWT via `Depends(get_current_user)`.
- Recommendations: Enforce `acting_user_id == user_id` (or explicit friend-based authorization) in `GET /map/{user_id}`.

**Security-definer SQL functions lack explicit search_path hardening:**
- Risk: Privileged trigger functions are defined without `SET search_path`, increasing attack surface for object shadowing in misconfigured schemas.
- Files: `backend/sql/v1.1_phase6_rls_policies.sql`
- Current mitigation: Trigger functions are `SECURITY DEFINER` and use schema-qualified table references.
- Recommendations: Add `SET search_path = public` on each security-definer function and keep all called function names schema-qualified.

**Client-side auth guard trusts localStorage token presence:**
- Risk: Route access decision is based on `localStorage` key existence instead of validated Supabase session state.
- Files: `frontend/src/router/index.js`, `frontend/src/lib/supabase.js`
- Current mitigation: Supabase calls still fail when token/session is invalid.
- Recommendations: Resolve auth state from `supabase.auth.getSession()` (or auth state listener) before navigation decisions.

## Performance Bottlenecks

**Per-request global matching computation:**
- Problem: `/match` loads all profiles and computes full similarity/distance matrices on each request.
- Files: `backend/routes/match.py`, `backend/services/matching/scoring.py`
- Cause: No caching/materialization; O(N^2) matrix creation repeats for every caller.
- Improvement path: Cache precomputed similarity/distance snapshots and invalidate on profile/interaction updates.

**Scheduler recomputes full graph for each user serially:**
- Problem: Timezone batch job calls `run_pipeline_for_user` per user, each call refetching all profiles/interactions and rerunning t-SNE pipeline.
- Files: `backend/services/map_pipeline/scheduler.py`, `backend/services/map_pipeline/__init__.py`, `backend/services/map_pipeline/data_fetcher.py`, `backend/services/map_pipeline/pipeline.py`
- Cause: Pipeline entrypoint is user-scoped but built on full-network data fetch/compute for every invocation.
- Improvement path: Fetch once per job run, compute shared matrices once, then derive per-user translated coordinates without refetching global inputs.

## Fragile Areas

**In-process scheduler tied to single-worker runtime:**
- Files: `backend/app.py`, `backend/services/map_pipeline/scheduler.py`
- Why fragile: Running with multiple Uvicorn workers duplicates scheduled jobs and causes repeated writes.
- Safe modification: Keep single-worker runtime or migrate to external scheduler/job store before changing deployment topology.
- Test coverage: No automated test verifies duplicate-job behavior under multi-worker deployment.

**RPC contract coupling across frontend/backend/database:**
- Files: `frontend/src/views/Home.vue`, `frontend/src/components/Post.vue`, `backend/routes/interactions.py`, `backend/routes/map.py`, `backend/services/map_pipeline/data_fetcher.py`
- Why fragile: String-based RPC names and payload shapes are duplicated across layers without shared typed contracts.
- Safe modification: Change one RPC at a time, update all callsites atomically, and add contract tests for request/response schemas.
- Test coverage: `backend/tests/test_contracts.py` covers FastAPI routes only; direct frontend-to-Supabase RPC contracts are untested.

## Scaling Limits

**Map pipeline minimum-size and compute constraints:**
- Current capacity: Pipeline requires at least 10 users (`N >= 10`) and runs TSNE with precomputed NxN distance matrix.
- Limit: Small datasets fail hard; large datasets experience steep compute growth and scheduler backlog risk.
- Scaling path: Add fallback embedding for `N < 10`, and move heavy map jobs to async workers with queueing + precomputation.

## Dependencies at Risk

**Backend dependency reproducibility is weak:**
- Risk: Critical backend packages are partially unpinned (`supabase`, `pydantic`, `jupyter`, `pytest`, `httpx`), and no lockfile exists.
- Impact: Environment drift can introduce runtime/test breakage without code changes.
- Migration plan: Pin exact versions in `backend/requirements.txt` and add deterministic lock generation for CI/dev parity.

## Missing Critical Features

**No CI-enforced quality gate:**
- Problem: Repository has no detected CI config and no enforced lint/type checks; frontend has no test script in `package.json`.
- Blocks: Safe refactoring velocity and reliable regression detection across UI + RPC integrations.

## Test Coverage Gaps

**Frontend auth/feed/profile flows are untested:**
- What's not tested: Route guards, signup/login flows, profile editing, post like/comment UX, and friend-request interactions.
- Files: `frontend/src/router/index.js`, `frontend/src/views/Login.vue`, `frontend/src/views/SignUp.vue`, `frontend/src/views/Profile.vue`, `frontend/src/views/Home.vue`, `frontend/src/components/Post.vue`
- Risk: UI-visible regressions and auth-state edge cases ship undetected.
- Priority: High

**Scheduler and persistence integration paths are largely untested:**
- What's not tested: `setup_scheduler` timezone registration behavior, job execution loops, and coordinate archival/insert behavior against real DB constraints.
- Files: `backend/services/map_pipeline/scheduler.py`, `backend/services/map_pipeline/coord_writer.py`, `backend/services/map_pipeline/data_fetcher.py`
- Risk: Silent operational failures in production jobs and inconsistent map snapshots.
- Priority: High

---

*Concerns audit: 2026-02-26*
