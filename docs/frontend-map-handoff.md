# Frontend Map Integration Handoff

Last updated: 2026-02-27

This document is for the frontend team to integrate map visualization with the current backend contract and to capture known UI issues discovered during manual QA.

## 1) Current QA Status (Frontend)

Manual test outcomes:

- PASS: Signup -> profile setup -> profile row creation works.
- PASS: Logout/login flow works.
- PASS: Protected route behavior works.
- PASS: Profile read/write flow works.
- PASS: Existing interaction-related UI actions work.
- PASS: No critical frontend runtime errors observed.
- N/A: Map screen visual compatibility test (no map screen currently exists in frontend).
- FAIL: Profile edit allows age less than 15.

## 2) Known Frontend Issues to Fix

### Issue A: Age validation bypass in profile edit

Observed behavior:

- In edit profile flow, age values below 15 are accepted.

Likely source:

- `frontend/src/views/Profile.vue` has age input without `min="15"` and no submit-time guard.

Expected fix:

1. Add UI constraint on input (`min="15"`, `max="100"`).
2. Add save-time validation before DB update.
3. Show actionable validation error message if invalid.

Recommended acceptance criteria:

- User cannot save age < 15.
- User cannot save age > 100.
- User sees clear error text when age is out of range.

### Issue B: Interest/language token normalization

Observed risk:

- Interests/languages are free-text comma-separated values.
- Current parsing trims whitespace only.
- `coding` and `Coding` are treated as different tokens, which can hurt similarity calculations.

Detailed impact:

- In the matching pipeline (`backend/services/matching/similarity.py`), Jaccard similarity uses raw set values as-is.
- That means all of these are treated as distinct tokens unless normalized before save:
  - `code`
  - `Code`
  - `coding`
  - `Coding`
- As a result, two users who are semantically similar can look artificially dissimilar.

Why this matters now:

- The map pipeline embedding stage lowercases feature tokens (`backend/services/map_pipeline/sparse_embedding.py`), so map behavior is less sensitive to case.
- The match endpoint similarity path still relies on raw token identity for interests/languages.
- Net effect: map-related behavior and match ranking can diverge in perceived quality if frontend input is inconsistent.

Expected fix:

1. Normalize on write: trim, lowercase, dedupe.
2. Optionally preserve display labels separately from normalized values.
3. Optionally maintain synonym mapping (for example, `js` -> `javascript`).
4. Move to a curated tag system to reduce semantic drift.

Recommended tag-system direction:

1. Define a canonical taxonomy source (for example: `coding`, `web-development`, `basketball`, `jazz`, `english`, `mandarin`).
2. Drive UI through searchable multi-select chips instead of arbitrary text.
3. Persist canonical IDs/keys, not free text labels.
4. Keep labels purely presentational and localizable.
5. Add migration/backfill strategy for existing free-text profile rows.

Suggested normalization fallback before full taxonomy is shipped:

- Client-side:
  - lowercase
  - trim
  - dedupe
  - optional alias map (`code`/`coding` -> `programming`)
- Backend-side safety:
  - normalize in `PUT /profile` path so non-frontend writers stay consistent.

Recommended normalization pipeline:

1. Split by comma.
2. Trim each token.
3. Convert to lowercase.
4. Remove empty tokens.
5. Deduplicate.
6. Sort for stable output (optional but recommended).

## 3) Map API Contract (Backend)

### Endpoint

- `GET /map/{user_id}`

### Auth behavior

- Requires bearer JWT.
- Self-only access is enforced by backend.
- If `acting_user_id != user_id`, backend returns `403`.

### Response shape

Top-level object:

- `user_id` (string)
- `version_date` (string date, `YYYY-MM-DD`)
- `computed_at` (string timestamp)
- `coordinates` (array)

Each coordinates item:

- `user_id` (string)
- `x` (number)
- `y` (number)
- `tier` (number)
- `nickname` (string)
- `is_suggestion` (boolean)

Reference implementation:

- `backend/routes/map.py`

### Trigger endpoint

- `POST /map/trigger/{user_id}`
- Self-only access (same 403 behavior).
- Intended for manual recompute trigger.

## 4) Frontend Rendering Guidance

### Coordinate semantics

- Requesting user is always centered at `(0,0)`.
- Primary nodes represent reciprocal/mutual graph neighbors.
- Suggestion nodes are additive fallback nodes where `is_suggestion = true`.

### Suggested visual mapping

- Center node (self): highest visual prominence.
- Mutuals (`is_suggestion=false`): primary style.
- Suggestions (`is_suggestion=true`): reduced emphasis (opacity/outline).
- Use `tier` for visual hierarchy (size/ring grouping/color intensity).

### Recommended UI states

- Loading: map skeleton/spinner.
- Empty/not ready (`404`): map not computed yet, show retry/help text.
- Unauthorized (`401`): route to login.
- Forbidden (`403`): self-only access message.
- Validation fail (`422` on trigger): show error details from backend.

## 5) Example Requests

Use your own API/JWT values.

```bash
API="http://127.0.0.1:8000"
SELF_USER_ID="<uuid>"
OTHER_USER_ID="<uuid>"
JWT_SELF="<access_token>"

# Should succeed (200)
curl -i "$API/map/$SELF_USER_ID" -H "Authorization: Bearer $JWT_SELF"

# Should fail (403)
curl -i "$API/map/$OTHER_USER_ID" -H "Authorization: Bearer $JWT_SELF"

# Optional trigger
curl -i -X POST "$API/map/trigger/$SELF_USER_ID" -H "Authorization: Bearer $JWT_SELF"
```

## 6) Suggested Frontend Acceptance Checklist

Mark all as complete before release:

- Map request uses logged-in user ID only.
- Map renders requester at center.
- Non-suggestion vs suggestion nodes are visually distinct.
- Metadata (`version_date`, `computed_at`) is displayed.
- Error states (401/403/404/422) are handled with user-friendly messages.
- Age validation bug fixed in edit profile.
- Interest/language normalization implemented.

## 7) Timezone System (Backend) and Frontend Integration

### How timezone works in backend today

Data model:

- `profiles.timezone` is a text column with default `UTC`.
- Added via migration: `backend/sql/v1.2_phase14_add_timezone_to_profiles.sql`.

Used in these backend behaviors:

1. Scheduler warm jobs:
   - At startup, scheduler reads distinct profile timezones via RPC (`get_distinct_timezones`).
   - Registers one warm-only cron job at local `19:00` for each timezone.
   - Code: `backend/services/map_pipeline/scheduler.py`.
2. User selection by timezone:
   - Warm job fetches users in the target timezone (`get_profiles_by_timezone`) and refreshes warm cache only.
3. Feature signals:
   - Sparse embedding includes timezone as a profile feature token (`timezone:<value>`).
   - Code: `backend/services/map_pipeline/sparse_embedding.py`.
4. Match model payload:
   - Profile timezone is read into `UserProfile` model (`backend/routes/match.py`).

Important runtime note:

- New timezone values are picked up for job registration only on scheduler startup.
- After adding users in a brand-new timezone, restart backend to register that timezone's 19:00 job.

### How frontend should connect timezone

Current gap:

- Frontend profile setup/edit does not expose timezone input.
- Backend supports timezone in profile writes.

Where to add timezone in frontend:

1. Profile setup page (`frontend/src/views/ProfileSetup.vue`):
   - Add timezone field to initial onboarding form.
   - Include `timezone` in `profiles.upsert({...})` payload.
2. Profile edit page (`frontend/src/views/Profile.vue`):
   - Add timezone field to edit form.
   - Include `timezone` in profile update payload.
3. Login flow (`frontend/src/views/Login.vue`):
   - Do not collect timezone directly in login credentials.
   - After login, check if profile timezone is missing/invalid.
   - If missing, route user to setup/edit profile prompt to set timezone.

Recommended UX choices:

- Use IANA timezone IDs (for example `America/New_York`, `Asia/Tokyo`, `UTC`).
- Default select value from browser timezone when available:
  - `Intl.DateTimeFormat().resolvedOptions().timeZone`
- Validate selected timezone against a known list before save.
- Persist canonical IANA string only.

Suggested acceptance criteria for timezone integration:

- New user can set timezone during onboarding.
- Existing user can change timezone in profile edit.
- Saved value is valid IANA ID.
- Backend receives and stores timezone value correctly.
- Scheduler behavior reflects timezone after backend restart for newly introduced timezone groups.
