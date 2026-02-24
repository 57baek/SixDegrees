# SixDegrees Database Schema

**Database:** Supabase PostgreSQL
**Note:** Frontend reads these tables directly via Supabase client (anon key). Frontend does NOT write directly to any table — all writes go through the backend API.

---

## user_profiles

Stores each user's profile data. This is the primary input to the People Map algorithm.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `user_id` | UUID | PRIMARY KEY | Matches Supabase Auth user ID (no FK constraint — seed/demo users may not have auth accounts) |
| `display_name` | TEXT | | Public display name shown on the map |
| `interests` | TEXT[] | | Array of interest tags (e.g. `["hiking", "photography"]`) |
| `location_city` | TEXT | | City name — note: column is `location_city`, NOT `city` |
| `location_state` | TEXT | | State or region code — note: column is `location_state`, NOT `state` (empty string for international users) |
| `age` | INTEGER | | Age in years |
| `languages` | TEXT[] | | Languages spoken (e.g. `["English", "Spanish"]`) |
| `field_of_study` | TEXT | | Academic discipline (e.g. `"computer science"`, `"biology"`) |
| `industry` | TEXT | | Professional industry (e.g. `"software"`, `"healthcare"`) |
| `education_level` | TEXT | | Highest degree (e.g. `"bachelors"`, `"masters"`, `"phd"`) |
| `timezone` | TEXT | | IANA timezone string (e.g. `"America/New_York"`) — used by scheduler to determine when the daily map update fires |
| `updated_at` | TIMESTAMPTZ | DEFAULT now() | Auto-updated timestamp |

**RLS:** Enabled. Frontend anon key can read all rows. Writes require service role key (backend only, via `PUT /profile`).

**Important column naming:** The DB columns are `location_city` and `location_state` (not `city` and `state`). The backend's `UserProfile` Pydantic model uses `city` and `state` internally — the `data_fetcher.py` translates at the DB boundary.

**Notes:**
- No foreign key from `user_id` to Supabase Auth `users` table — seed/demo users may not have auth accounts; a FK would block inserts
- `timezone` determines when the daily map recomputation fires for this user (19:00 in that timezone)
- All array fields (`interests`, `languages`) default to empty arrays when null

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
  .from('user_profiles')
  .select('display_name, interests, location_city, location_state, age')
  .eq('user_id', userId)
  .single()
```

**Do NOT use the service role key in the frontend.** The service role key bypasses all RLS policies and must only be used in the backend server. The backend sets it via the `SUPABASE_KEY` environment variable.

---

## Summary: What the Frontend Can and Cannot Do

| Operation | Frontend (anon key) | Backend (service role key) |
|-----------|--------------------|-----------------------------|
| Read `user_profiles` | Yes | Yes |
| Write `user_profiles` | No — use `PUT /profile` | Yes |
| Read `interactions` | Yes | Yes |
| Write `interactions` | No — use `POST /interactions/*` | Yes |
| Read `map_coordinates` | Yes | Yes |
| Write `map_coordinates` | No — pipeline only | Yes |
