# Phase 1: Database Foundation - Research

**Researched:** 2026-02-22
**Domain:** Supabase PostgreSQL schema creation, seed data, Python client
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Table schemas
- `user_profiles`: user_id (UUID), display_name, interests (text[]), location_city, location_state, age, languages (text[]), field_of_study, industry, education_level, timezone, updated_at
- `interactions`: user_id_a (UUID), user_id_b (UUID), likes_count (int), comments_count (int), dm_count (int), last_updated; canonical pair order enforced (user_id_a < user_id_b)
- `map_coordinates`: id, center_user_id (UUID), other_user_id (UUID), x (float), y (float), tier (1/2/3), computed_at, is_current (boolean)

#### Canonical pair ordering
Interactions stored with user_id_a < user_id_b (lexicographic UUID comparison). Prevents duplicate rows. All query/write code must enforce this ordering.

#### `is_current` versioning
`map_coordinates` table stores both old and new rows — old rows marked `is_current=false`, new rows `is_current=true`. Do NOT delete old rows; they support future animation delta computation.

#### Index requirement
`map_coordinates` needs a composite index on `(center_user_id, is_current)` for fast API reads. This is critical for serving precomputed maps.

#### Seed data quantity and diversity
At least 15 users required (t-SNE is unstable below 10). Users must have:
- Varied interests (the algorithm's heaviest-weighted field at 35%)
- Different timezones (scheduler groups by timezone)
- Mixed ages, locations, languages
- Seeded interaction counts that are non-trivial (to verify algorithm sensitivity)

#### RLS / service role key
Backend must use the Supabase **service role key** (not anon key) to bypass RLS. Verify after table creation that reads work without RLS errors.

#### No Supabase migrations file required
This project doesn't use a migrations directory. Tables are created directly via the Supabase dashboard SQL editor or a one-time setup script.

### Claude's Discretion

Nothing listed as discretion in CONTEXT.md — all decisions are locked.

### Deferred Ideas (OUT OF SCOPE)

- Any algorithm code
- Any API endpoints
- Any scheduler code
- Frontend changes
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DB-01 | `user_profiles` table exists in Supabase with fields: user_id (UUID), display_name, interests (text[]), location_city, location_state, age, languages (text[]), field_of_study, industry, education_level, timezone, updated_at | SQL CREATE TABLE pattern with `text[]` arrays and `gen_random_uuid()` default; verified via Supabase PostgreSQL docs |
| DB-02 | `interactions` table exists in Supabase with fields: user_id_a (UUID), user_id_b (UUID), likes_count, comments_count, dm_count, last_updated; pair stored in canonical order (a < b) | UNIQUE constraint on `(user_id_a, user_id_b)` with a CHECK constraint enforcing `user_id_a < user_id_b`; upsert via supabase-py `.upsert(..., on_conflict='user_id_a,user_id_b')` |
| DB-03 | `map_coordinates` table exists in Supabase with fields: id, center_user_id (UUID), other_user_id (UUID), x (float), y (float), tier (1/2/3), computed_at, is_current (boolean) | Standard CREATE TABLE; `is_current` boolean default true; `tier` smallint with CHECK(tier IN (1,2,3)) |
| DB-04 | `map_coordinates` has index on (center_user_id, is_current) for fast API reads | `CREATE INDEX ... ON map_coordinates (center_user_id, is_current)` — verified from Supabase PostgreSQL index docs |
| DB-05 | Seed script populates at least 15 mock users with varied profiles (diverse interests, locations, ages) and seeded interaction counts into Supabase | supabase-py `.insert([...list of dicts...]).execute()` for batch insert; interests/languages as Python lists (auto-converted to `text[]` by the client) |
</phase_requirements>

---

## Summary

Phase 1 is entirely SQL schema definition plus a Python seed script. There is no algorithm, no API, and no scheduler work. The deliverables are: three tables created in the Supabase dashboard (or via a setup SQL script), one composite index, and a Python script that uses the existing supabase-py client to insert 15+ seed users with realistic diversity.

The existing backend already has `config/supabase.py` which creates a Supabase client using the service role key from `.env`. The seed script should import this existing client rather than creating its own. The `user_profiles` schema closely mirrors the existing `UserProfile` Pydantic model in `models/user.py` (with `city`/`state` renamed to `location_city`/`location_state` and `user_id` replacing `id`, plus `display_name` and `timezone` added).

The key risk area is correctly seeding the `interactions` table with canonical pair order enforced. The seed script must always store `min(uuid_a, uuid_b)` as `user_id_a`. Lexicographic string comparison on UUIDs works correctly for this purpose in Python. There is no algorithmic complexity — this phase is pure data setup.

**Primary recommendation:** Create the three tables via a single SQL setup script (run once in Supabase dashboard), then write a Python seed script at `backend/scripts/seed_db.py` that uses the existing supabase-py client to insert 15+ diverse users and interaction pairs.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| supabase-py | Already installed (pinned via `requirements.txt`) | Supabase Python client for inserts, upserts, selects | Already used in `config/supabase.py`; no new dependency |
| python-dotenv | 1.0.0 (already in requirements) | Load `.env` for SUPABASE_URL/SUPABASE_KEY | Already used in `config/supabase.py` |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| uuid (stdlib) | Python stdlib | Generate deterministic UUIDs for seed data | `uuid.uuid4()` for new users; no extra install |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| supabase-py insert | psycopg2 / SQLAlchemy direct connection | Direct DB connection (DATABASE_URL in .env.example) is available but adds complexity. supabase-py already configured and tested. |
| SQL setup script via dashboard | Alembic / Supabase migrations | CONTEXT.md explicitly says no migrations directory — dashboard SQL editor or one-time script only |

**Installation:** No new packages required. All dependencies already in `backend/requirements.txt`.

---

## Architecture Patterns

### Recommended Project Structure

```
backend/
├── config/
│   └── supabase.py          # existing — import this, don't recreate
├── scripts/
│   └── seed_db.py           # NEW: seed script (run once from backend/ dir)
└── sql/
    └── setup_tables.sql     # NEW: one-time SQL to paste into Supabase dashboard
```

The `scripts/` directory is referenced in `CLAUDE.md` (mentions `scripts/test_map.py` and `scripts/people_map_demo.ipynb`) but does not exist yet. Phase 1 establishes it with `seed_db.py`.

### Pattern 1: Table Creation SQL

**What:** CREATE TABLE statements using PostgreSQL features available in Supabase (UUID, text[], timestamptz, boolean, smallint, CHECK constraint, UNIQUE constraint)
**When to use:** Run once in Supabase dashboard SQL editor, or via a setup script

```sql
-- Source: Supabase official docs / Context7 /llmstxt/supabase_llms_txt

-- user_profiles table
CREATE TABLE public.user_profiles (
    user_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    display_name   TEXT NOT NULL,
    interests      TEXT[] NOT NULL DEFAULT '{}',
    location_city  TEXT NOT NULL DEFAULT '',
    location_state TEXT NOT NULL DEFAULT '',
    age            INTEGER NOT NULL,
    languages      TEXT[] NOT NULL DEFAULT '{}',
    field_of_study TEXT NOT NULL DEFAULT '',
    industry       TEXT NOT NULL DEFAULT '',
    education_level TEXT NOT NULL DEFAULT '',
    timezone       TEXT NOT NULL DEFAULT 'UTC',
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- interactions table (canonical pair order enforced by CHECK)
CREATE TABLE public.interactions (
    user_id_a      UUID NOT NULL,
    user_id_b      UUID NOT NULL,
    likes_count    INTEGER NOT NULL DEFAULT 0,
    comments_count INTEGER NOT NULL DEFAULT 0,
    dm_count       INTEGER NOT NULL DEFAULT 0,
    last_updated   TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id_a, user_id_b),
    CONSTRAINT canonical_pair_order CHECK (user_id_a < user_id_b)
);

-- map_coordinates table
CREATE TABLE public.map_coordinates (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    center_user_id UUID NOT NULL,
    other_user_id  UUID NOT NULL,
    x              FLOAT NOT NULL,
    y              FLOAT NOT NULL,
    tier           SMALLINT NOT NULL CHECK (tier IN (1, 2, 3)),
    computed_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    is_current     BOOLEAN NOT NULL DEFAULT TRUE
);

-- Composite index for fast API reads (DB-04)
CREATE INDEX idx_map_coordinates_center_is_current
    ON public.map_coordinates (center_user_id, is_current);
```

### Pattern 2: Batch Insert via supabase-py

**What:** Insert multiple rows in one call using a list of dicts. `text[]` columns accept Python lists natively — the supabase-py client serializes them correctly.
**When to use:** Seed script inserting 15+ user profiles and interaction pairs

```python
# Source: Context7 /supabase/supabase-py
from config.supabase import get_supabase_client

supabase = get_supabase_client()

users = [
    {
        "user_id": str(uuid.uuid4()),
        "display_name": "Alice Chen",
        "interests": ["hiking", "photography", "cooking"],
        "location_city": "San Francisco",
        "location_state": "CA",
        "age": 28,
        "languages": ["English", "Mandarin"],
        "field_of_study": "computer science",
        "industry": "technology",
        "education_level": "bachelors",
        "timezone": "America/Los_Angeles",
    },
    # ... 14+ more users
]

response = supabase.table("user_profiles").insert(users).execute()
assert len(response.data) == len(users), "Seed insert failed"
```

### Pattern 3: Canonical Pair Ordering for Interactions

**What:** Enforce user_id_a < user_id_b in Python before inserting. UUID strings compare lexicographically in Python, which is consistent with the CHECK constraint.
**When to use:** Every interaction insert/upsert

```python
def canonical_pair(uid_a: str, uid_b: str) -> tuple[str, str]:
    """Return (smaller_uuid, larger_uuid) for canonical pair ordering."""
    return (uid_a, uid_b) if uid_a < uid_b else (uid_b, uid_a)

# Usage in seed script:
a, b = canonical_pair(user_ids[0], user_ids[1])
interaction = {
    "user_id_a": a,
    "user_id_b": b,
    "likes_count": 5,
    "comments_count": 3,
    "dm_count": 1,
}
supabase.table("interactions").insert(interaction).execute()
```

### Pattern 4: Upsert for Interactions (future write endpoints)

**What:** Use upsert with `on_conflict` to increment counts without duplicating rows. Phase 1 only seeds, but understanding this pattern is important for seeding idempotency.
**When to use:** When rerunning the seed script should not error on duplicate pairs

```python
# Source: Context7 /supabase/supabase-py
response = supabase.table("interactions").upsert(
    interaction,
    on_conflict="user_id_a,user_id_b"
).execute()
```

### Anti-Patterns to Avoid

- **Inserting interaction rows without enforcing canonical order in Python:** The DB CHECK constraint will reject them, causing confusing 400 errors. Always sort in Python before inserting.
- **Using the anon key for the seed script:** The seed script runs with service role key. Using anon key fails on tables with RLS enabled. The existing `config/supabase.py` already uses the service role key — import it, don't create a new client.
- **Storing interests/languages as JSON strings:** The schema uses `text[]` (PostgreSQL arrays). Pass Python lists; the supabase-py client handles serialization. Don't serialize to JSON strings.
- **Seeding all users with identical interests:** The algorithm's most-weighted field is interests (35%). Homogeneous seed data makes the algorithm output meaningless and the demo unimpressive.
- **Seeding only one timezone:** The scheduler groups users by timezone. At least 3 different timezones are needed to verify scheduler grouping logic in Phase 4.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| UUID generation | Custom ID generator | Python stdlib `uuid.uuid4()` | Standard, collision-free, correct format for Supabase UUID columns |
| Batch insert | Loop of individual inserts | `supabase.table(...).insert([...list...]).execute()` | Single network call; supabase-py handles the list natively |
| Canonical pair ordering | Complex comparison logic | `min(a, b), max(a, b)` on UUID strings | Python string comparison on UUID4 strings is deterministic and matches `<` in PostgreSQL |
| Conflict handling on re-seed | Delete-then-insert | `.upsert(..., on_conflict="user_id_a,user_id_b")` | Idempotent re-runs without error |

**Key insight:** This phase is 90% SQL DDL and 10% Python data generation. Don't over-engineer. The seed script is a one-time utility, not production code.

---

## Common Pitfalls

### Pitfall 1: `text[]` Array Serialization

**What goes wrong:** Inserting Python lists into `text[]` columns fails if you accidentally JSON-stringify them first (e.g., `json.dumps(["hiking", "photography"])` gives a string, not an array).
**Why it happens:** Confusion between JSON arrays and PostgreSQL arrays.
**How to avoid:** Pass Python lists directly. supabase-py uses PostgREST which handles `text[]` via native PostgreSQL array syntax when given a Python list.
**Warning signs:** Insert succeeds but the column value reads as a JSON string `'["hiking","photography"]'` instead of `{hiking,photography}`.

### Pitfall 2: Service Role Key vs. Anon Key

**What goes wrong:** Seed script errors with `401 Unauthorized` or silently returns 0 rows due to RLS.
**Why it happens:** Using the anon key (`SUPABASE_ANON_KEY`) instead of service role key (`SUPABASE_KEY`). The `.env.example` shows `SUPABASE_KEY` is the service role key.
**How to avoid:** Import from `config.supabase` which already loads the service role key. Run the seed script from the `backend/` directory with the venv activated so `python-dotenv` picks up `.env`.
**Warning signs:** Insert call returns `response.data = []` or raises an HTTP 401/403.

### Pitfall 3: Seed Script Working Directory

**What goes wrong:** `from config.supabase import get_supabase_client` fails with `ModuleNotFoundError`.
**Why it happens:** Python path resolution when running from `backend/scripts/seed_db.py` — the `backend/` directory isn't on `sys.path` by default if run as `python scripts/seed_db.py` from the project root.
**How to avoid:** Run the seed script from inside `backend/`: `cd backend && python scripts/seed_db.py`. Or add `sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))` at the top of the script.
**Warning signs:** `ModuleNotFoundError: No module named 'config'`.

### Pitfall 4: Homogeneous Seed Data Breaks t-SNE

**What goes wrong:** t-SNE produces meaningless clusters, demo looks like random noise, algorithm appears broken.
**Why it happens:** Seeding users with too-similar profiles (e.g., all "technology" industry, all 25-year-olds) makes similarity scores near-uniform. t-SNE on a near-constant distance matrix produces nonsense.
**How to avoid:** Deliberately vary interests across clearly distinct clusters (e.g., 4-5 users who all like "hiking/photography", 4-5 who like "music/concerts", 4-5 who like "gaming/anime"). Also vary ages (20–55), locations (multiple states), and languages.
**Warning signs:** Demo scatter plot shows all users in a tight cluster with no visible structure.

### Pitfall 5: Insufficient Timezone Coverage

**What goes wrong:** Phase 4 scheduler implementation has no variety to test against.
**Why it happens:** Seeding all users with `America/Los_Angeles` or `UTC`.
**How to avoid:** Include at least 3–4 distinct timezones in seed data (e.g., `America/New_York`, `America/Chicago`, `America/Los_Angeles`, `Europe/London`).
**Warning signs:** `SELECT DISTINCT timezone FROM user_profiles` returns only one row.

### Pitfall 6: table already exists on re-run

**What goes wrong:** Running the SQL setup script twice errors with `relation already exists`.
**Why it happens:** Plain `CREATE TABLE` without `IF NOT EXISTS`.
**How to avoid:** Use `CREATE TABLE IF NOT EXISTS` in the setup SQL. Add `IF NOT EXISTS` to the index creation as well.

---

## Code Examples

Verified patterns from official sources:

### Batch Insert (supabase-py)

```python
# Source: Context7 /supabase/supabase-py
response = supabase.table("user_profiles").insert([
    {"display_name": "Alice", "interests": ["hiking", "cooking"], ...},
    {"display_name": "Bob",   "interests": ["gaming", "music"],  ...},
]).execute()
print(f"Inserted {len(response.data)} users")
```

### Select with Filter

```python
# Source: Context7 /supabase/supabase-py
response = supabase.table("user_profiles").select("*").execute()
profiles = response.data  # list of dicts
```

### Composite Index (SQL)

```sql
-- Source: Supabase official docs / Context7 /llmstxt/supabase_llms_txt
CREATE INDEX IF NOT EXISTS idx_map_coordinates_center_is_current
    ON public.map_coordinates (center_user_id, is_current);
```

### Upsert with Conflict Target (supabase-py)

```python
# Source: Context7 /supabase/supabase-py
response = supabase.table("interactions").upsert(
    {"user_id_a": a, "user_id_b": b, "likes_count": 5, ...},
    on_conflict="user_id_a,user_id_b"
).execute()
```

### Verify RLS Bypass Works (verification step)

```python
# After table creation, run this to confirm service role key bypasses RLS
response = supabase.table("user_profiles").select("count", count="exact").execute()
print(f"Row count: {response.count}")  # Should not raise 401/403
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| supabase-py v1 (different API) | supabase-py v2 (current; `.table().insert().execute()` pattern) | 2023 | The `.execute()` call at the end is required; old v1 patterns without `.execute()` don't work |
| `supabase.table().insert(data)` without `.execute()` | Must chain `.execute()` | supabase-py v2 | Forgetting `.execute()` returns a query builder, not data |

**Deprecated/outdated:**
- Direct PostgreSQL psycopg2 usage for seed: Still works (DATABASE_URL in .env.example) but unnecessary — supabase-py already set up.
- `from supabase import create_client` called with anon key: Works for reads without RLS but will fail on tables with RLS enabled; always use service role key for backend operations.

---

## Seed Data Design

This section is specific to this phase since DB-05 requires thoughtful seed design.

### Minimum 15 users, recommended 20

t-SNE requires N >= 10 (pipeline raises error below this). 15 is the stated minimum; 20 gives better t-SNE output and more realistic demo.

### Interest Cluster Design (supports demo sensitivity)

Design seed users in clear clusters to make the demo visually compelling:

| Cluster | Interests | Count |
|---------|-----------|-------|
| Outdoors | hiking, camping, photography, rock climbing | 4 users |
| Creative | music, concerts, painting, film | 4 users |
| Tech/Gaming | gaming, programming, anime, sci-fi | 4 users |
| Social/Food | cooking, travel, wine, yoga | 4 users |
| Sports | soccer, basketball, fitness, running | 3-4 users |

Cross-cluster users (e.g., 1-2 users who share interests from two clusters) make the map more interesting.

### Interaction Seeding (non-trivial counts required)

Seed interactions between users within the same cluster more heavily than across clusters. This ensures the algorithm can demonstrate sensitivity:

```python
# Within-cluster: 5-15 likes, 3-8 comments, 0-3 DMs
# Cross-cluster: 0-3 likes, 0-1 comments, 0 DMs
# A few "power pairs" with very high counts to test 95th-pct clipping later
```

### Timezone Distribution

Minimum required (for Phase 4 scheduler):
- `America/New_York` — 4-5 users
- `America/Chicago` — 2-3 users
- `America/Los_Angeles` — 4-5 users
- `Europe/London` — 2-3 users
- `Asia/Tokyo` — 1-2 users (bonus)

### Field Values Compatible with Existing similarity.py

The existing `similarity.py` has defined category maps for `field_of_study` and `industry`. Use values from these maps to ensure the algorithm's tiered similarity works correctly:

**Valid `field_of_study` values:** `"computer science"`, `"data science"`, `"software engineering"`, `"business administration"`, `"finance"`, `"psychology"`, `"graphic design"`, `"music"`, `"biology"`, `"marketing"`

**Valid `industry` values:** `"software"`, `"technology"`, `"finance"`, `"healthcare"`, `"education"`, `"media"`, `"entertainment"`, `"retail"`, `"research"`

**Valid `education_level` values (from model):** `"bachelors"`, `"masters"`, `"phd"`, `"highschool"`

---

## Open Questions

1. **Does `user_profiles.user_id` need to reference `auth.users`?**
   - What we know: The schema in CONTEXT.md shows `user_id UUID PRIMARY KEY` without a foreign key constraint specified. The existing `users` table in Supabase is a "legacy" table being superseded.
   - What's unclear: Should `user_id` be a FK to `auth.users(id)`? This would be correct for production but complicates seeding with mock data (mock users wouldn't exist in auth.users).
   - Recommendation: For Phase 1 (seed data phase), do NOT add FK to auth.users. The seed script generates standalone UUIDs. FK constraint can be added later when real user auth is wired up.

2. **Should `interactions.user_id_a` and `user_id_b` FK to `user_profiles.user_id`?**
   - What we know: CONTEXT.md doesn't specify FK constraints on interactions.
   - What's unclear: Adding FKs would provide referential integrity but complicates seed order (profiles must be inserted before interactions).
   - Recommendation: Add FK constraints. Seed profiles first, then interactions. The seed script should insert in this order regardless.

3. **RLS policy on new tables?**
   - What we know: Backend uses service role key which bypasses RLS entirely. CONTEXT.md says to verify service role reads work. RLS policies are not specified in CONTEXT.md.
   - What's unclear: Should we enable RLS at all for Phase 1? Enabling RLS with no policies means nobody can read/write via anon key — but the backend doesn't use anon key.
   - Recommendation: Enable RLS on all three tables (`ALTER TABLE ... ENABLE ROW LEVEL SECURITY`) but add no policies. This means only the service role key can access the tables — correct for this architecture. Frontend reads map_coordinates directly (CLAUDE.md), so a SELECT policy for authenticated users on map_coordinates may be needed — but that is out of scope for Phase 1.

---

## Sources

### Primary (HIGH confidence)
- Context7 `/supabase/supabase-py` — insert, upsert, select patterns; `.execute()` requirement; `on_conflict` parameter
- Context7 `/llmstxt/supabase_llms_txt` — CREATE TABLE, RLS, CREATE INDEX SQL patterns; service role bypass; multi-row insert
- `/Users/BAEK/Code/sixDegrees/backend/config/supabase.py` — existing client setup confirmed; service role key via `SUPABASE_KEY` env var
- `/Users/BAEK/Code/sixDegrees/backend/services/matching/similarity.py` — valid field_of_study and industry values for seed data compatibility
- `/Users/BAEK/Code/sixDegrees/backend/models/user.py` — valid education_level values; field name mapping (city→location_city, state→location_state)
- `/Users/BAEK/Code/sixDegrees/.planning/phases/01-database-foundation/CONTEXT.md` — locked schema decisions

### Secondary (MEDIUM confidence)
- `/Users/BAEK/Code/sixDegrees/backend/.env.example` — confirms SUPABASE_KEY is service role key (not anon key); DATABASE_URL available as alternative

### Tertiary (LOW confidence)
- None

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — supabase-py already installed and configured; SQL patterns verified via Context7
- Architecture: HIGH — schema locked by CONTEXT.md; directory structure mirrors CLAUDE.md conventions
- Pitfalls: HIGH for service role/RLS and canonical ordering (verified from code); MEDIUM for seed data design (best-practice recommendation, not hard requirement)
- Seed data design: MEDIUM — cluster design is a recommendation to maximize demo quality; not mandated by requirements

**Research date:** 2026-02-22
**Valid until:** 2026-04-22 (Supabase stable, supabase-py API stable; re-verify if supabase-py major version changes)
