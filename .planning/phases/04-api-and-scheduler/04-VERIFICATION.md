---
phase: 04-api-and-scheduler
verified: 2026-02-23T17:30:00Z
status: passed
score: 14/14 must-haves verified
re_verification: false
human_verification:
  - test: "Send POST /interactions/like with valid JWT and verify Supabase interactions row is actually incremented"
    expected: "likes_count in the interactions table increments by 1; canonical pair ordering enforced (user_id_a < user_id_b)"
    why_human: "Cannot call Supabase RPC in a test without live credentials; database state cannot be verified statically"
  - test: "Confirm APScheduler fires CronTrigger at 19:00 in each unique timezone"
    expected: "For each unique timezone in user_profiles, one job fires at exactly 19:00 local time"
    why_human: "Real-time trigger firing cannot be verified without running the scheduler live until 19:00 in a registered timezone"
  - test: "Call PUT /profile with body containing a different user_id than the JWT subject"
    expected: "HTTP 403 with detail 'Cannot update another user's profile'"
    why_human: "Requires a live Supabase JWT to exercise the ownership guard end-to-end"
---

# Phase 4: API and Scheduler Verification Report

**Phase Goal:** The People Map is accessible via HTTP, interaction events and profile data are written through backend endpoints with JWT validation, and daily batch recomputation runs automatically per user timezone
**Verified:** 2026-02-23T17:30:00Z
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Any write endpoint can extract and validate a Supabase JWT by importing get_current_user from routes/deps.py | VERIFIED | `from routes.deps import get_current_user` imports cleanly; HTTPBearer(auto_error=False) + supabase.auth.get_user(token) + AuthApiError catch all present |
| 2 | A missing or invalid Bearer token causes get_current_user to raise HTTP 401 | VERIFIED | Explicit `if credentials is None` raises HTTPException(401); AuthApiError catch raises HTTPException(401) — both cases covered |
| 3 | A valid JWT returns the authenticated user's UUID string | VERIFIED | `return response.user.id` present; `response.user is None` guard present before return |
| 4 | GET /map/{user_id} returns JSON with user_id, computed_at, and a coordinates list | VERIFIED | _fetch_map_response() builds exactly `{"user_id", "computed_at", "coordinates": [...]}` from map_coordinates table |
| 5 | Each coordinate entry contains user_id, x, y, tier, and display_name | VERIFIED | Coordinate dict in map.py includes all five fields; display_name fetched via single .in_() call to user_profiles |
| 6 | The requesting user appears at (0.0, 0.0) in their own map | VERIFIED | coord_writer (Phase 3) guarantees a row where other_user_id == center_user_id at (0.0, 0.0); map.py returns all is_current rows including this one (no special handling needed) |
| 7 | GET /map/{user_id} with no precomputed map returns HTTP 404 with exact message | VERIFIED | `raise HTTPException(status_code=404, detail="Map not yet computed for this user")` present |
| 8 | POST /map/trigger/{user_id} triggers pipeline and returns updated coordinates | VERIFIED | Calls `run_pipeline_for_user(user_id)` then returns `_fetch_map_response(user_id)`; ValueError mapped to HTTP 422 |
| 9 | All three interaction endpoints require JWT and atomically increment the correct column | VERIFIED | All three endpoints have `Depends(get_current_user)`; _record_interaction calls `increment_interaction` RPC with correct column argument |
| 10 | Interaction endpoints enforce canonical pair ordering and reject self-interaction | VERIFIED | `min()/max()` enforces uid_a < uid_b; `acting_user_id == target_user_id` guard raises HTTP 400 |
| 11 | PUT /profile creates or updates the authenticated user's profile row | VERIFIED | `upsert(payload, on_conflict="user_id")` present; payload built from JWT user_id + non-None body fields only |
| 12 | PUT /profile rejects writing another user's profile with HTTP 403 | VERIFIED | `if body.user_id is not None and body.user_id != acting_user_id: raise HTTPException(403)` present |
| 13 | APScheduler starts via lifespan, registers one CronTrigger per unique timezone at 19:00, and runs pipeline per user with per-user error isolation | VERIFIED | scheduler.py has setup_scheduler() with CronTrigger(hour=19, minute=0, timezone=tz) per unique timezone; per-user try/except in _run_pipeline_for_timezone(); app.py lifespan calls setup_scheduler().start() and scheduler.shutdown() |
| 14 | Single-worker constraint is documented and apscheduler is version-pinned to 3.x | VERIFIED | SINGLE WORKER CONSTRAINT comment in both scheduler.py docstring and app.py top comment; `apscheduler>=3.10,<4` in requirements.txt; installed version is 3.11.2 |

**Score:** 14/14 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/routes/deps.py` | Reusable get_current_user FastAPI dependency | VERIFIED | 50 lines; HTTPBearer(auto_error=False); supabase.auth.get_user(token); AuthApiError (not bare except); returns response.user.id |
| `backend/routes/map.py` | GET /map/{user_id} and POST /map/trigger/{user_id} endpoints | VERIFIED | 59 lines; router with prefix="/map"; _fetch_map_response() shared helper; both routes confirmed by import test |
| `backend/routes/interactions.py` | POST /interactions/like, /comment, /dm endpoints | VERIFIED | 63 lines; router with prefix="/interactions"; three endpoints with Depends(get_current_user); _record_interaction helper with min()/max() and self-loop guard |
| `backend/routes/profile.py` | PUT /profile endpoint | VERIFIED | 52 lines; router with prefix="/profile"; Depends(get_current_user); 403 ownership guard; non-None-only payload construction; upsert on user_id |
| `backend/services/map_pipeline/scheduler.py` | setup_scheduler() returning configured AsyncIOScheduler | VERIFIED | 91 lines; setup_scheduler() returns AsyncIOScheduler; CronTrigger per unique timezone; per-user/per-timezone error isolation; single-worker constraint documented |
| `backend/app.py` | FastAPI app with lifespan, CORS, and all Phase 4 routers | VERIFIED | asynccontextmanager lifespan; setup_scheduler().start() on startup; scheduler.shutdown() on teardown; all 4 routers included via include_router(); single-worker comment at top |
| `backend/requirements.txt` | apscheduler>=3.10,<4 dependency pin | VERIFIED | `apscheduler>=3.10,<4` present on last line; installed version is 3.11.2 |
| `backend/sql/add_increment_interaction_rpc.sql` | SQL migration file documenting increment_interaction function | VERIFIED | File exists; contains CREATE OR REPLACE FUNCTION increment_interaction with INSERT...ON CONFLICT DO NOTHING + UPDATE col+1 pattern |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| backend/routes/deps.py | supabase.auth.get_user(token) | HTTPBearer(auto_error=False) + explicit None-check + AuthApiError catch | WIRED | Line 36: `response = sb.auth.get_user(token)`; line 44: `except AuthApiError:` |
| backend/routes/deps.py | config.supabase.get_supabase_client | import | WIRED | Line 8: `from config.supabase import get_supabase_client` |
| backend/routes/map.py | supabase map_coordinates table | .select().eq('center_user_id', ...).eq('is_current', True) | WIRED | Lines 11-17: full query chain present; `map_coordinates` table name literal used |
| backend/routes/map.py | services.map_pipeline.run_pipeline_for_user | import in trigger endpoint | WIRED | Line 3: `from services.map_pipeline import run_pipeline_for_user`; line 55: called in trigger_map() |
| backend/routes/map.py | supabase user_profiles table | display_name lookup via single .in_() | WIRED | Lines 23-29: `.table("user_profiles").select("user_id, display_name").in_("user_id", other_ids)` |
| backend/routes/interactions.py | routes.deps.get_current_user | Depends(get_current_user) | WIRED | Lines 44, 52, 60: all three endpoints have `Depends(get_current_user)` |
| backend/routes/interactions.py | supabase.rpc('increment_interaction', ...) | get_supabase_client().rpc() | WIRED | Lines 33-36: `get_supabase_client().rpc("increment_interaction", {...}).execute()` |
| backend/routes/profile.py | routes.deps.get_current_user | Depends(get_current_user) | WIRED | Line 33: `acting_user_id: str = Depends(get_current_user)` |
| backend/routes/profile.py | supabase user_profiles table | .upsert({...}, on_conflict='user_id').execute() | WIRED | Lines 47-49: `.table("user_profiles").upsert(payload, on_conflict="user_id").execute()` |
| backend/app.py | backend/services/map_pipeline/scheduler.py | from services.map_pipeline.scheduler import setup_scheduler | WIRED | Line 13: import present; lines 19-20: `setup_scheduler().start()` in lifespan |
| backend/app.py | backend/routes/map.py | app.include_router(map_router) | WIRED | Line 42: `app.include_router(map_router)` |
| backend/app.py | backend/routes/interactions.py | app.include_router(interactions_router) | WIRED | Line 43: `app.include_router(interactions_router)` |
| backend/app.py | backend/routes/profile.py | app.include_router(profile_router) | WIRED | Line 44: `app.include_router(profile_router)` |
| backend/services/map_pipeline/scheduler.py | services.map_pipeline.run_pipeline_for_user | import at top of module | WIRED | Line 22: `from services.map_pipeline import run_pipeline_for_user`; line 43: called in _run_pipeline_for_timezone() |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| AUTH-01 | 04-01, 04-03 | Backend validates Supabase JWT on all write endpoints using supabase.auth.get_user(token); returns HTTP 401 for missing or invalid tokens | SATISFIED | deps.py: HTTPBearer(auto_error=False) + None check + AuthApiError catch → 401; Depends(get_current_user) on all write endpoints |
| API-01 | 04-02 | GET /map/{user_id} returns precomputed coordinates from map_coordinates table — no live computation at request time | SATISFIED | map.py GET reads from map_coordinates with is_current=True; no pipeline call in GET path |
| API-02 | 04-02 | Response format: { user_id, computed_at, coordinates: [{ user_id, x, y, tier, display_name }] } | SATISFIED | _fetch_map_response() returns exactly this shape; all five coordinate fields present |
| API-03 | 04-02 | The requesting user always appears in coordinates list at (0.0, 0.0) | SATISFIED | coord_writer (Phase 3) inserts center user at (0.0, 0.0); map.py returns all is_current rows without filtering this row out |
| API-04 | 04-02 | If user_id has no precomputed map, returns 404 with message "Map not yet computed for this user" | SATISFIED | `raise HTTPException(status_code=404, detail="Map not yet computed for this user")` exact string present |
| API-05 | 04-02 | POST /map/trigger/{user_id} manually triggers pipeline recomputation for a single user | SATISFIED | trigger_map() calls run_pipeline_for_user() then returns _fetch_map_response(); ValueError → 422 |
| SCHED-01 | 04-04 | APScheduler (AsyncIOScheduler) starts with the FastAPI app via lifespan context manager | SATISFIED | app.py: asynccontextmanager lifespan; setup_scheduler().start(); startup confirmed by uvicorn test showing "Application startup complete" |
| SCHED-02 | 04-04 | Scheduler registers one CronTrigger per unique timezone in user_profiles, firing at 19:00 in that timezone | SATISFIED | scheduler.py: CronTrigger(hour=19, minute=0, timezone=tz) per unique timezone extracted from user_profiles |
| SCHED-03 | 04-04 | On trigger, scheduler groups all users with that timezone and runs the full pipeline for all of them | SATISFIED | _run_pipeline_for_timezone() re-queries user_profiles.eq("timezone", timezone) at fire time and calls run_pipeline_for_user() per user |
| SCHED-04 | 04-04 | Single-worker constraint is documented | SATISFIED | Full SINGLE WORKER CONSTRAINT block in scheduler.py docstring; comment in app.py line 3 |
| WRITE-01 | 04-03 | POST /interactions/like — JWT auth; upserts interactions row incrementing likes_count | SATISFIED | record_like() has Depends(get_current_user); calls _record_interaction(..., "likes_count"); RPC enforces canonical pair order |
| WRITE-02 | 04-03 | POST /interactions/comment — JWT auth; upserts interactions row incrementing comments_count | SATISFIED | record_comment() has Depends(get_current_user); calls _record_interaction(..., "comments_count") |
| WRITE-03 | 04-03 | POST /interactions/dm — JWT auth; upserts interactions row incrementing dm_count | SATISFIED | record_dm() has Depends(get_current_user); calls _record_interaction(..., "dm_count") |
| WRITE-04 | 04-03 | PUT /profile — JWT auth; creates or updates authenticated user's row in user_profiles; user can only update their own profile | SATISFIED | update_profile() has Depends(get_current_user); 403 guard for body.user_id != acting_user_id; upsert on user_id |

**All 14 requirements satisfied.**

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| backend/routes/auth.py | 2-3 | TODO stubs for POST /register and POST /login | INFO | auth.py is a pre-existing stub not belonging to Phase 4; no router from it is registered in app.py; does not affect Phase 4 goal |

No blockers or warnings found in Phase 4 files.

---

### Human Verification Required

#### 1. Live interaction write to Supabase

**Test:** Send `POST /interactions/like` with a valid Supabase JWT and `{"target_user_id": "<other-uuid>"}`. Then query the `interactions` table in Supabase.
**Expected:** A row exists with `user_id_a = min(acting, target)`, `user_id_b = max(acting, target)`, and `likes_count` incremented by 1.
**Why human:** Requires live Supabase credentials to issue a real JWT and to verify the database state after the RPC call. Static analysis cannot confirm the RPC executes correctly against the live database.

#### 2. APScheduler CronTrigger fires at 19:00 per timezone

**Test:** With at least one user_profile row containing a valid timezone (e.g., "America/New_York"), start the server and wait until 19:00 Eastern. Check server logs for "Scheduler: running pipeline for N users in timezone America/New_York".
**Expected:** The log line appears at 19:00 local time; pipeline runs for all users in that timezone.
**Why human:** Real-time trigger firing cannot be verified statically. Would require running the server for up to 24 hours.

#### 3. JWT ownership guard on PUT /profile

**Test:** Obtain two valid Supabase JWTs for user A and user B. Send `PUT /profile` with user A's JWT but `{"user_id": "<user-B-uuid>", "display_name": "hacked"}`.
**Expected:** HTTP 403 with `{"detail": "Cannot update another user's profile"}`.
**Why human:** Requires live Supabase JWTs to produce the token payload. Static analysis confirms the guard logic is present, but end-to-end behavior requires a real auth token.

---

### Gaps Summary

No gaps. All 14 must-haves verified at all three levels (exists, substantive, wired). All 14 requirement IDs from the plan frontmatter (AUTH-01, API-01 through API-05, SCHED-01 through SCHED-04, WRITE-01 through WRITE-04) are satisfied by concrete, non-stub implementations.

The only pre-existing stub found (`backend/routes/auth.py`) predates Phase 4, is not registered in app.py, and is documented as out-of-scope for this milestone in CLAUDE.md.

---

_Verified: 2026-02-23T17:30:00Z_
_Verifier: Claude (gsd-verifier)_
