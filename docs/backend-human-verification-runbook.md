# Backend Human Verification Runbook (Phases 21-23, 26)

Last updated: 2026-02-27

Use this runbook to complete the remaining environment-level checks that automated tests cannot fully prove.

## Scope

This covers human verification requirements from:

- Phase 21: Compute engine and publish validation
- Phase 22: Ego map API and compatibility serving
- Phase 23: Scheduler operations and safe rollout
- Phase 26: Profiles-only convergence path-B reset and republish promotion gate

## 0) Preflight

Before testing:

1. Use a non-production Supabase environment.
2. Ensure backend env is configured:
   - `SUPABASE_URL`
   - `SUPABASE_KEY` (service role)
3. Start API locally:

```bash
cd backend
source venv/bin/activate
uvicorn app:app --reload
```

4. Prepare two users:
   - `SELF_USER_ID` (authenticated user)
   - `OTHER_USER_ID` (different user)
5. Prepare one valid JWT for `SELF_USER_ID`.

Environment shortcuts:

```bash
API="http://127.0.0.1:8000"
SELF_USER_ID="<self_uuid>"
OTHER_USER_ID="<other_uuid>"
JWT_SELF="<jwt_token>"
```

## 1) Phase 22 API Contract Checks (Live)

### Test 1.1: Self map read should succeed

```bash
curl -i "$API/map/$SELF_USER_ID" \
  -H "Authorization: Bearer $JWT_SELF"
```

Expected:

- HTTP `200`
- Response includes top-level fields:
  - `user_id`
  - `version_date`
  - `computed_at`
  - `coordinates`

### Test 1.2: Cross-user map read should be denied

```bash
curl -i "$API/map/$OTHER_USER_ID" \
  -H "Authorization: Bearer $JWT_SELF"
```

Expected:

- HTTP `403`

### Test 1.3: Trigger endpoint self-only behavior

```bash
# Self trigger
curl -i -X POST "$API/map/trigger/$SELF_USER_ID" \
  -H "Authorization: Bearer $JWT_SELF"

# Cross-user trigger
curl -i -X POST "$API/map/trigger/$OTHER_USER_ID" \
  -H "Authorization: Bearer $JWT_SELF"
```

Expected:

- Self trigger: `200` or `422` (depending on compute/publish gates)
- Cross-user trigger: `403`

## 2) Phase 21 Publish Validation (Live DB)

### Test 2.1: Fail-closed publish behavior

Goal:

- If validation fails, no new served version should replace the prior good version.

Procedure:

1. Capture current served metadata:

```bash
curl -s "$API/map/$SELF_USER_ID" \
  -H "Authorization: Bearer $JWT_SELF" | jq '{version_date, computed_at}'
```

2. Run a compute attempt in a blocked scenario (staging fixture or known invalid case).
3. Fetch map metadata again using the same command.

Expected:

- Post-run `version_date`/`computed_at` remain unchanged when validation blocks publish.

### Test 2.2: Diagnostics permissions and readback

Goal:

- Service role writes diagnostics.
- Authenticated read RPC returns expected payload.
- Unauthorized direct writes are blocked.

Procedure:

1. Execute one successful run and one blocked run.
2. In Supabase SQL editor, query diagnostics RPC(s):

```sql
-- Example: adjust call signature to your deployed function
select * from public.get_compute_run_diagnostics(null);
```

3. Confirm entries include run status, gate outcomes, metrics, and timings.
4. Attempt unauthorized direct insert as non-service context.

Expected:

- Diagnostics are present for both success and blocked runs.
- Authenticated read path works as intended.
- Unauthorized direct write is denied by policy/permissions.

## 3) Phase 23 Scheduler Runtime Checks

### Test 3.1: UTC midnight recompute cadence

Goal:

- Exactly one global recompute at `00:00 UTC`.

Procedure:

1. Observe deployed-like logs across the UTC boundary.
2. Count global recompute executions.

Expected:

- One global recompute job at midnight UTC.
- No duplicate recompute jobs.

### Test 3.2: 19:00 local warm-only behavior

Goal:

- 19:00 local jobs should only warm cache and never recompute globally.

Procedure:

1. Observe logs for one 19:00 local trigger window.
2. Verify invoked code path indicates warm refresh only.

Expected:

- Warm cache refresh happens.
- No global recompute invoked.

## 4) Phase 23 Legacy Drop Safety Gate

### Test 4.1: Guarded migration behavior

Migration file:

- `backend/sql/v2_phase23_trigger_validation_and_legacy_drop.sql`

Goal:

- Migration blocks unsafe drops when dependencies exist.
- Drops `user_profiles` only when all guards pass.

Procedure:

1. Run migration against a staging clone with realistic dependencies.
2. Validate failure mode when dependencies are present.
3. Validate success mode when prerequisites/dependencies are fully clear.

Expected:

- Dependency/precondition errors are explicit and fail-closed.
- No accidental destructive drop when checks fail.

## 5) Suggested Evidence to Capture

For final sign-off, capture:

- Terminal output for each `curl` request (`-i` headers included).
- JSON snippets showing `version_date`/`computed_at` before/after blocked publish.
- Screenshot/export of diagnostics RPC output.
- Scheduler log snippets around UTC midnight and local 19:00.
- Migration execution logs for both blocked and allowed scenarios.

## 6) Pass/Fail Report Template

Use this template and fill in result per test:

- 1.1 Self map read: PASS/FAIL
- 1.2 Cross-user map read: PASS/FAIL
- 1.3 Trigger self/cross-user behavior: PASS/FAIL
- 2.1 Fail-closed publish preserves prior version: PASS/FAIL
- 2.2 Diagnostics permission/readback: PASS/FAIL
- 3.1 UTC midnight single recompute: PASS/FAIL
- 3.2 19:00 warm-only no recompute: PASS/FAIL
- 4.1 Legacy-drop gate migration safety: PASS/FAIL
- 5.1 Phase 26 staging migration reset/drop sequence: PASS/FAIL
- 5.2 Phase 26 republish after reset: PASS/FAIL

Notes:

- Include any status code mismatch, unexpected payload fields, or log anomalies.

## 7) Phase 26 staging verification

### Test 5.1: Staging migration executes preflight -> reset -> drop in order

Migration file:

- `backend/sql/v2_phase26_profiles_only_reset_and_republish.sql`

Goal:

- Verify the migration fails closed on dependencies and only drops `public.user_profiles` after preflight checks pass.
- Verify path-B reset clears legacy global rows before republish.

Procedure:

1. Snapshot staging baseline counts:

```sql
select count(*) as map_rows from public.map_coordinates;
select to_regclass('public.user_profiles') as user_profiles_table;
```

2. Execute `backend/sql/v2_phase26_profiles_only_reset_and_republish.sql` in staging.
3. Validate post-migration state:

```sql
select count(*) as map_rows_after_reset from public.map_coordinates;
select to_regclass('public.user_profiles') as user_profiles_table_after;
```

Expected:

- Migration errors explicitly if dependency preflight fails.
- On success, `map_rows_after_reset = 0` and `user_profiles_table_after` is `NULL`.

### Test 5.2: Republish one fresh global coordinate version after reset

Goal:

- Confirm operators can republish a fresh global map version after reset before production promotion.

Procedure:

1. Trigger one full republish from the API (staging):

```bash
curl -i -X POST "$API/map/trigger/$SELF_USER_ID" \
  -H "Authorization: Bearer $JWT_SELF"
```

2. Verify fresh global rows and metadata:

```sql
select count(*) as republished_rows from public.map_coordinates;
select version_date, computed_at, count(*) as row_count
from public.map_coordinates
group by version_date, computed_at
order by computed_at desc;
```

Expected:

- Trigger returns `200` (or explicit `422` if publish gates reject, with no partial write).
- Successful republish produces non-zero `republished_rows` and a single fresh `version_date/computed_at` batch.

Promotion criteria:

- Both tests pass on staging first.
- Evidence bundle includes migration output, reset counts, trigger response, and republish metadata query results.
