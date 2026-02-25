# SixDegrees Database Schema

**Database:** Supabase PostgreSQL
**Version:** 1.1 (Phase 17 — v1.2 migration complete)
**Note:** Frontend reads these tables directly via Supabase client (anon key). Frontend may write directly to `profiles`; all other writes go through the backend API.

---

## profiles

The canonical profile table. This is the primary input to the People Map algorithm and the table used by both the backend and frontend.

`user_profiles` was the previous algorithm input table — it has been **dropped in v1.2**. All backend code now reads from and writes to `profiles`.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PRIMARY KEY | Matches Supabase Auth user ID (no FK constraint — seed/demo users may not have auth accounts) |
| `nickname` | TEXT | UNIQUE | Public username shown on the map |
| `interests` | TEXT[] | | Array of interest tags (e.g. `["hiking", "photography"]`) |
| `city` | TEXT | | City name |
| `state` | TEXT | | State or region code (empty string for international users) |
| `age` | SMALLINT | | Age in years |
| `languages` | TEXT[] | | Languages spoken (e.g. `["English", "Spanish"]`) |
| `education` | TEXT | | Academic discipline (e.g. `"Computer Science"`, `"Biology"`) |
| `occupation` | TEXT | | Job title (nullable) |
| `industry` | TEXT | | Professional industry (e.g. `"software"`, `"healthcare"`) |
| `timezone` | TEXT | NOT NULL DEFAULT 'UTC' | IANA timezone string (e.g. `"America/New_York"`) — used by scheduler to determine when the daily map update fires. **Added in v1.2 migration.** |
| `is_onboarded` | BOOLEAN | DEFAULT false | `false` until the user completes profile setup. Used to redirect to `/profile-setup`. |
| `profile_tier` | SMALLINT | | Which friend tier can see your profile (1 = only closest friends, 6 = everyone) — frontend-managed, backend ignores |
| `friends` | UUID[] | | Array of user IDs the user is friends with — frontend-managed, backend ignores |
| `pending_friend_requests` | UUID[] | | Array of user IDs who have sent a friend request — frontend-managed, backend ignores |
| `rejected_friends` | UUID[] | | User IDs whose requests were declined — frontend-managed, backend ignores |
| `created_at` | TIMESTAMPTZ | DEFAULT now() | Row creation timestamp |

**RLS:** Enabled. Frontend anon key can read and write (frontend writes profile directly). Backend uses service role key for map/match algorithm reads and `PUT /profile` upsert.

**Notes:**
- No foreign key from `id` to Supabase Auth `users` table — seed/demo users may not have auth accounts; a FK would block inserts
- `timezone` determines when the daily map recomputation fires for this user (19:00 in that timezone)
- All array fields (`interests`, `languages`, `friends`, etc.) default to empty arrays when null
- `education_level` was removed in v1.2 — that field is not in `profiles` and weight was redistributed to `interests` (now 40%)

---

## user_profiles (dropped in v1.2)

> **Deprecated.** The `user_profiles` table was the previous algorithm input table. It has been dropped in v1.2 and replaced by `profiles`. All backend code has been migrated to `profiles`. Do not reference `user_profiles` in new code.

---

## interactions

Stores pairwise interaction counts between users. Each row represents a unique user pair — all interaction types between those two users are combined in one row.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `user_id_a` | UUID | NOT NULL, PK part | Lower UUID of the pair (enforced by CHECK constraint) |
| `user_id_b` | UUID | NOT NULL, PK part | Higher UUID of the pair |
| `likes_count` | INTEGER | DEFAULT 0 | Cumulative number of likes between this pair (bidirectional) |
| `comments_count` | INTEGER | DEFAULT 0 | Cumulative number of comments between this pair |
| `dm_count` | INTEGER | DEFAULT 0 | Cumulative number of direct messages between this pair |
| `last_updated` | TIMESTAMPTZ | DEFAULT now() | Timestamp of the most recent interaction event |

**PRIMARY KEY:** `(user_id_a, user_id_b)`

**Canonical pair ordering:** The pair is always stored using canonical order — the lexicographically smaller UUID as `user_id_a` and the larger as `user_id_b`. This is enforced by:
1. A `CHECK` constraint in the database: `user_id_a < user_id_b`
2. Python enforcement in the backend before every write: `uid_a = min(acting_id, target_id)`

The frontend does NOT need to enforce this — the backend API (`POST /interactions/*`) handles ordering automatically before writing.

**Interaction counts are bidirectional:** A single row covers both directions — if user A likes user B and user B likes user A, both increments go to the same `likes_count` field in the same row.

**Atomic write pattern:** Counts are incremented via a Postgres RPC function (`increment_interaction`) using `INSERT ... ON CONFLICT DO NOTHING` followed by `UPDATE col = col + 1`. This prevents race conditions and avoids the standard upsert problem (which would reset counts to 0 on conflict).

**RLS:** Enabled. Reads allowed via anon key. Writes require service role key (backend only, via `POST /interactions/*` endpoints).

**FK note:** `user_id_a` and `user_id_b` FKs are being migrated to reference `profiles.id` — handled by the DB team after backend migration completes.

**Adding new interaction types:** Add a new `INTEGER DEFAULT 0` column (e.g. `shares_count`) and add a corresponding entry to `INTERACTION_WEIGHTS` in `backend/config/algorithm.py`. No other code changes required — the algorithm picks up the new column automatically.

---

## map_coordinates

Stores the precomputed 2D (x, y) coordinates for each user pair. The pipeline writes a full new set of rows on every run; old rows are retained with `is_current = false` for future animation support (smooth transitions between daily updates).

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PRIMARY KEY, DEFAULT gen_random_uuid() | Row identifier |
| `center_user_id` | UUID | NOT NULL | The user whose perspective this map represents |
| `other_user_id` | UUID | NOT NULL | A user appearing on `center_user_id`'s map |
| `x` | FLOAT | | Horizontal coordinate — center user's own row is always 0.0 |
| `y` | FLOAT | | Vertical coordinate — center user's own row is always 0.0 |
| `tier` | INTEGER | CHECK (tier IN (1, 2, 3)) | Proximity tier: 1 = closest 5, 2 = next 10, 3 = outer ring |
| `computed_at` | TIMESTAMPTZ | DEFAULT now() | When this coordinate set was computed by the pipeline |
| `is_current` | BOOLEAN | DEFAULT true | `true` = part of the most recent pipeline run; `false` = historical row |

**Index:** `(center_user_id, is_current)` — used by `GET /map/{user_id}` for fast reads.

**The `is_current` versioning pattern:** When the pipeline runs for a user:
1. All existing rows for that `center_user_id` with `is_current = true` are marked `is_current = false`
2. A new set of rows is inserted with `is_current = true`
3. Old rows are NEVER deleted — they are retained for future animation delta computation (smooth transitions between daily positions)

**Reading the current map:** Query with `.eq("center_user_id", userId).eq("is_current", true)`.

**The center user's own row:** The center user always appears as a row in their own map with `other_user_id = center_user_id` and `x = 0.0, y = 0.0, tier = 1`. This row is what enables the frontend to display the center user at the origin.

**RLS:** Enabled. Frontend anon key can read all rows. Writes require service role key (backend only, via the pipeline triggered by scheduler or `POST /map/trigger/{user_id}`).

---

## posts

Stores user-created posts for the social feed.

**RLS:** Enabled. Reads allowed via anon key. Writes go through frontend directly (Supabase client).

**FK:** `user_id → profiles.id`

---

## likes

Stores post likes.

**RLS:** Enabled. Reads allowed via anon key. Writes go through frontend directly.

**FK:** `user_id → profiles.id`

---

## comments

Stores post comments.

**RLS:** Enabled. Reads allowed via anon key. Writes go through frontend directly.

**FK:** `user_id → profiles.id`

---

## Supabase Client Setup (Frontend)

```javascript
import { createClient } from '@supabase/supabase-js'

const supabase = createClient(
  import.meta.env.VITE_SUPABASE_URL,     // from .env
  import.meta.env.VITE_SUPABASE_ANON_KEY // anon key — safe for frontend reads
)

// Read current map for a user
const { data, error } = await supabase
  .from('map_coordinates')
  .select('other_user_id, x, y, tier')
  .eq('center_user_id', userId)
  .eq('is_current', true)

// Read a user's profile
const { data: profile } = await supabase
  .from('profiles')
  .select('nickname, interests, city, state, age')
  .eq('id', userId)
  .single()
```

**Do NOT use the service role key in the frontend.** The service role key bypasses all RLS policies and must only be used in the backend server. The backend sets it via the `SUPABASE_KEY` environment variable.

---

## Summary: What the Frontend Can and Cannot Do

| Operation | Frontend (anon key) | Backend (service role key) |
|-----------|--------------------|-----------------------------|
| Read `profiles` | Yes | Yes |
| Write `profiles` | Yes (direct Supabase) | Yes (via `PUT /profile`) |
| Read `interactions` | Yes | Yes |
| Write `interactions` | No — use `POST /interactions/*` | Yes |
| Read `map_coordinates` | Yes | Yes |
| Write `map_coordinates` | No — pipeline only | Yes |
