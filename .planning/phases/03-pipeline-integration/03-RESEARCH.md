# Phase 3: Pipeline Integration - Research

**Researched:** 2026-02-22
**Domain:** supabase-py 2.28.0 PostgREST client — read from Supabase, write to Supabase, orchestrate DB-connected pipeline
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- Phase 3 adds two new files to `backend/services/map_pipeline/`: `data_fetcher.py` and `coord_writer.py`. No other existing files are modified.
- `data_fetcher.py` reads all rows from `user_profiles` and `interactions` via the Supabase Python client from `config/supabase.py` (service role key, bypasses RLS). Returns structured Python objects suitable for passing to Phase 2 algorithm modules.
- Column names in `user_profiles` are `location_city`/`location_state` (not `city`/`state`). `data_fetcher.py` must map `location_city` → `city` and `location_state` → `state` when constructing `UserProfile` objects (this was documented as deferred from Phase 2).
- `coord_writer.py` write order is mandatory: (1) mark all existing rows for `center_user_id` where `is_current=true` as `is_current=false`, (2) insert new rows with `is_current=true`, (3) do NOT delete old rows — retained for future animation delta.
- Every write includes the requesting user at (0.0, 0.0) alongside all other users — the `run_pipeline()` output already includes the requesting user in `translated_results`.
- Canonical pair ordering: when reading interactions for a given (i, j) pair, code must handle both orderings (the DB enforces `user_id_a < user_id_b` but lookups can come from either direction).
- No FK from `user_profiles` to `auth.users` — seed users don't exist in `auth.users`; `data_fetcher.py` reads directly from `user_profiles` with no join.
- N < 10 guard: if fewer than 10 users are in the DB, propagate the t-SNE error clearly before calling t-SNE.
- A top-level orchestrator function chains: `data_fetcher.fetch_all()` → Phase 2 `run_pipeline()` → `coord_writer.write_coordinates(center_user_id, results)`. This is the function the Phase 4 scheduler and trigger endpoint will call.
- No anon key usage anywhere in backend — service role key is mandatory.

### Claude's Discretion

None specified.

### Deferred Ideas (OUT OF SCOPE)

- API endpoints (Phase 4)
- Scheduler (Phase 4)
- JWT validation
- Modifying existing `matching/` routes
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DATA-01 | `data_fetcher.py` reads all user profiles from `user_profiles` table via Supabase Python client | `supabase.table("user_profiles").select("*").execute()` — confirmed pattern from supabase-py 2.28.0 docs; response.data is a list of dicts |
| DATA-02 | `data_fetcher.py` reads all interaction counts from `interactions` table for the set of user_ids being processed | `supabase.table("interactions").select("*").execute()` — full table read; filter by user_ids if needed via `.in_()` filter; canonical pair lookup requires handling both (a,b) and (b,a) orderings |
| DATA-03 | Backend uses service role key (not anon key) to bypass Supabase RLS | Already established in `config/supabase.py` — `SUPABASE_KEY = os.getenv("SUPABASE_KEY")` is service role key; RLS enabled on all 3 tables (Phase 1); service role bypasses RLS by design |
| STORE-01 | After computing new coordinates, write step marks all existing `is_current=true` rows for that `center_user_id` as `is_current=false` before inserting new rows | `supabase.table("map_coordinates").update({"is_current": False}).eq("center_user_id", uid).eq("is_current", True).execute()` — confirmed update+filter pattern from supabase-py docs |
| STORE-02 | Previous coordinate rows are retained (not deleted) to support future animation delta computation | Update `is_current=false` only — no DELETE call; supabase-py `update()` pattern confirmed |
| STORE-03 | Each write stores both the requesting user themselves at (0,0) and all other users in the coordinate set | `run_pipeline()` already returns requesting user in `translated_results` at (0.0, 0.0) with tier=1; `coord_writer` bulk-inserts all rows from `translated_results` without filtering |
</phase_requirements>

---

## Summary

Phase 3 adds DB wiring around the Phase 2 pure computation pipeline. The work is almost entirely `supabase-py` CRUD: read all profiles and interactions from Supabase, pass them to the existing `run_pipeline()` function, then write the results back to `map_coordinates`. There is no new algorithm logic in Phase 3.

The supabase-py 2.28.0 client (already installed in the venv) has a stable PostgREST query builder with a simple chained API: `.table("name").select("*").execute()` for reads, `.update({...}).eq("col", val).execute()` for filtered updates, and `.insert([...]).execute()` for bulk inserts. All responses have a `.data` attribute containing a list of dicts.

The key implementation details are: (1) field name mapping when constructing `UserProfile` objects from DB rows (`location_city` → `city`, `location_state` → `state`), (2) the mandatory two-step write order in `coord_writer.py` (update old rows first, then insert new), and (3) the canonical pair key reconstruction for the interaction dict that `run_pipeline()` expects.

**Primary recommendation:** Keep both `data_fetcher.py` and `coord_writer.py` as simple, stateless functions with zero algorithm logic. Each function does one thing — fetch or write — and delegates everything else to the existing modules. The top-level orchestrator in `map_pipeline/__init__.py` or a `pipeline_db.py` file chains fetch → compute → write.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| supabase-py | 2.28.0 (installed) | Read from/write to Supabase tables | Already in venv; established pattern from seed_db.py and config/supabase.py |
| models.user.UserProfile | existing | Data model accepted by run_pipeline() | Must reuse existing model to call Phase 2 modules without modification |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| datetime (stdlib) | Python stdlib | `computed_at` timestamp for coord_writer inserts | Use `datetime.now(timezone.utc).isoformat()` for UTC timestamps |
| typing (stdlib) | Python stdlib | Type hints on all function signatures | All new functions should have typed return types |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Full table read for interactions | Filter by user_ids in DB query | Full read is simpler and correct at 20 users; filter optimization is SCALE-01 (v2). Not needed now. |
| Two-step write (update + insert) | Upsert on (center_user_id, other_user_id) | Upsert would require a unique constraint; the current schema has no unique constraint on that pair. Update+insert is the correct pattern for this schema. |

**Installation:**
```bash
# supabase-py already installed in backend/venv
# No new dependencies required for Phase 3
```

---

## Architecture Patterns

### Recommended Project Structure

```
backend/services/map_pipeline/
├── __init__.py              # existing (empty)
├── interaction.py           # existing Phase 2
├── scoring.py               # existing Phase 2
├── tsne_projector.py        # existing Phase 2
├── origin_translator.py     # existing Phase 2
├── pipeline.py              # existing Phase 2 orchestrator (pure computation)
├── data_fetcher.py          # NEW Phase 3: reads user_profiles + interactions
└── coord_writer.py          # NEW Phase 3: writes map_coordinates
```

The top-level DB-connected orchestrator can be added to `map_pipeline/__init__.py` or as a new `pipeline_db.py`. It wraps `run_pipeline()` with fetch and write.

### Pattern 1: data_fetcher.py

**What:** Reads all rows from `user_profiles` and `interactions`, returns typed data structures matching `run_pipeline()` input contract.

**Key mapping:** DB column `location_city` → `UserProfile.city`, `location_state` → `UserProfile.state`. The DB also has `display_name` (not in UserProfile model); `data_fetcher.py` must capture it separately for `coord_writer.py` (not needed — coord_writer only writes user_id, x, y, tier, computed_at).

**Interaction dict reconstruction:** The `run_pipeline()` interaction arg is `dict[tuple[str,str], dict[str,int]]` with canonical pair key `(uid_a, uid_b)` where `uid_a < uid_b`. The DB rows already have canonical ordering, so reconstruction is direct.

```python
# Source: supabase-py 2.28.0 docs + seed_db.py established pattern
from config.supabase import get_supabase_client
from models.user import UserProfile

def fetch_all() -> tuple[list[UserProfile], dict[tuple[str, str], dict[str, int]]]:
    """Read all user_profiles and interactions from Supabase.

    Returns:
        (users, raw_interaction_counts) where:
        - users: list[UserProfile] with city/state mapped from location_city/location_state
        - raw_interaction_counts: {(uid_a, uid_b): {"likes": int, "comments": int, "dms": int}}
          Keys are already canonical (uid_a < uid_b) because DB enforces this.
    """
    sb = get_supabase_client()

    # Read all profiles
    profiles_response = sb.table("user_profiles").select("*").execute()
    users = []
    for row in profiles_response.data:
        users.append(UserProfile(
            id=row["user_id"],
            interests=row["interests"] or [],
            languages=row["languages"] or [],
            city=row["location_city"],       # DB: location_city → model: city
            state=row["location_state"],     # DB: location_state → model: state
            education_level=row["education_level"],
            field_of_study=row["field_of_study"],
            occupation="",                   # not stored in DB; default to empty string
            industry=row["industry"],
            age=row["age"],
        ))

    # Read all interactions
    interactions_response = sb.table("interactions").select("*").execute()
    raw_interaction_counts = {}
    for row in interactions_response.data:
        pair_key = (row["user_id_a"], row["user_id_b"])  # already canonical in DB
        raw_interaction_counts[pair_key] = {
            "likes":    row["likes_count"],
            "comments": row["comments_count"],
            "dms":      row["dm_count"],
        }

    return users, raw_interaction_counts
```

**Note on `occupation` field:** `UserProfile` has an `occupation` field but `user_profiles` table does not have this column (Phase 1 DDL does not include it). The existing matching module's `build_similarity_matrix()` may reference `.occupation`. Research shows the matching/similarity.py uses occupation for... let's check this is handled safely.

### Pattern 2: coord_writer.py

**What:** Writes pipeline results to `map_coordinates`. Mandatory two-step write order.

```python
# Source: supabase-py 2.28.0 update+insert pattern (confirmed from docs)
from datetime import datetime, timezone
from config.supabase import get_supabase_client

def write_coordinates(
    center_user_id: str,
    translated_results: list[dict],
) -> None:
    """Write map coordinates for a single center_user_id.

    Mandatory write order (STORE-01, STORE-02):
    1. Mark all existing is_current=True rows as is_current=False (DO NOT DELETE)
    2. Insert new rows with is_current=True

    Args:
        center_user_id: The user whose map is being written.
        translated_results: list[{"user_id": str, "x": float, "y": float, "tier": int}]
                           from run_pipeline()["translated_results"].
                           Must include center_user_id at (0.0, 0.0).
    """
    sb = get_supabase_client()
    now = datetime.now(timezone.utc).isoformat()

    # STORE-01: mark old rows as not current (NEVER DELETE — STORE-02)
    sb.table("map_coordinates") \
      .update({"is_current": False}) \
      .eq("center_user_id", center_user_id) \
      .eq("is_current", True) \
      .execute()

    # STORE-03: insert all users including center user at (0,0)
    rows = [
        {
            "center_user_id": center_user_id,
            "other_user_id":  entry["user_id"],
            "x":              entry["x"],
            "y":              entry["y"],
            "tier":           entry["tier"],
            "computed_at":    now,
            "is_current":     True,
        }
        for entry in translated_results
    ]
    sb.table("map_coordinates").insert(rows).execute()
```

### Pattern 3: DB-Connected Orchestrator

**What:** Wraps fetch → compute → write for a single user. This is what Phase 4 scheduler and trigger endpoint will call.

```python
# In map_pipeline/__init__.py or pipeline_db.py
from services.map_pipeline.data_fetcher import fetch_all
from services.map_pipeline.pipeline import run_pipeline
from services.map_pipeline.coord_writer import write_coordinates

def run_pipeline_for_user(requesting_user_id: str) -> None:
    """Full DB-connected pipeline for one user.

    Raises ValueError if N < 10 (propagated from run_pipeline).
    """
    users, raw_interaction_counts = fetch_all()
    result = run_pipeline(users, raw_interaction_counts, requesting_user_id)
    write_coordinates(requesting_user_id, result["translated_results"])
```

### Anti-Patterns to Avoid

- **Deleting old map_coordinates rows:** Use `update(is_current=False)` only. DELETE violates STORE-02 (rows needed for future animation delta).
- **Inserting before marking old rows:** The update step MUST come before the insert. If reversed, new rows may be incorrectly marked as not-current by a concurrent call.
- **Using the anon key:** `config/supabase.py` uses `SUPABASE_KEY` which must be the service role key. RLS is enabled on all 3 tables; anon key will receive permission denied errors.
- **Calling `auth.users` or doing a join on `user_profiles` to `auth.users`:** Seed users don't exist in `auth.users`. Read `user_profiles` directly with no join.
- **Reconstructing canonical pairs at the wrong direction:** DB guarantees `user_id_a < user_id_b`. The pair key read from DB rows is already canonical. Do not re-sort — just use `(row["user_id_a"], row["user_id_b"])` directly.
- **Hardcoding `occupation`:** The `UserProfile` model has `.occupation` but the DB table does not. Pass `occupation=""` (empty string) when constructing from DB rows. The `build_similarity_matrix()` in `matching/scoring.py` may use occupation — verify it doesn't break with empty string.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| DB reads | Custom HTTP requests to PostgREST | `supabase.table().select().execute()` | supabase-py wraps PostgREST; already installed and used in seed_db.py |
| Bulk insert | Loop of single inserts | `supabase.table().insert(list_of_dicts).execute()` | supabase-py supports bulk insert with a list; avoids N round trips |
| Timestamp formatting | Custom datetime → string | `datetime.now(timezone.utc).isoformat()` | Standard ISO 8601; Supabase/PostgreSQL parses TIMESTAMPTZ correctly from this format |
| Pair key canonicalization | Custom sort logic | Read directly from DB (`user_id_a`, `user_id_b`) — already canonical | DB has CHECK constraint enforcing canonical order; re-sorting is unnecessary noise |

**Key insight:** Phase 3's value is wiring — not new logic. Every complex operation (normalization, t-SNE, tier assignment) is already built in Phase 2. Phase 3 is <100 lines of Python total.

---

## Common Pitfalls

### Pitfall 1: `occupation` Field Missing from DB

**What goes wrong:** `UserProfile(occupation=row["occupation"])` raises `KeyError` — the `user_profiles` table has no `occupation` column.
**Why it happens:** `UserProfile` Pydantic model has `occupation: str` but the DB DDL from Phase 1 (`backend/sql/setup_tables.sql`) does not include this column.
**How to avoid:** Pass `occupation=""` (empty string) as a default when constructing `UserProfile` from DB rows. Verify `matching/similarity.py` handles empty string for occupation without error.
**Warning signs:** `KeyError: 'occupation'` on the first `fetch_all()` call.

### Pitfall 2: Write Order Reversal

**What goes wrong:** New rows get marked `is_current=False` if a concurrent pipeline run updates before the fresh insert completes.
**Why it happens:** If INSERT happens before UPDATE, the new rows have `is_current=True`, and then the UPDATE marks ALL `is_current=True` rows false — including the ones just inserted.
**How to avoid:** Always UPDATE (mark old false) before INSERT (add new true). Never reverse this order.
**Warning signs:** After writing, query returns 0 rows where `is_current=True` for a user — all rows were marked false.

### Pitfall 3: N < 10 Not Propagating Clearly

**What goes wrong:** If DB has fewer than 10 users, `run_pipeline()` raises `ValueError` from `tsne_projector.py`. If uncaught by the orchestrator, Phase 4 will receive an unhandled exception.
**Why it happens:** `project_tsne()` raises `ValueError: t-SNE pipeline requires at least 10 users` when N < 10.
**How to avoid:** The orchestrator (`run_pipeline_for_user`) can let the ValueError propagate naturally — it has a clear message. Phase 4 scheduler should catch and log it. Don't swallow the exception in Phase 3.
**Warning signs:** Pipeline silently does nothing, or returns partial results when N < 10.

### Pitfall 4: Supabase Response Structure

**What goes wrong:** Accessing `response["data"]` instead of `response.data` — supabase-py returns an object, not a dict.
**Why it happens:** Confusion between HTTP response dict and supabase-py's typed response object.
**How to avoid:** Always use `response.data` (attribute access). This is consistent with `seed_db.py` which already uses `response.data`.
**Warning signs:** `TypeError: 'APIResponse' object is not subscriptable`.

### Pitfall 5: Partial Reads for Large User Sets

**What goes wrong:** supabase-py has a default page size limit (PostgREST default is 1000 rows). With 20 seed users this is not an issue, but the planner should note this for production.
**Why it happens:** PostgREST by default limits rows returned per request.
**How to avoid:** For the current 20-user seed, `select("*").execute()` returns all rows within the default limit. Note this as a SCALE-01 concern (v2). At Phase 3 scale (20 users), not a blocking issue.
**Warning signs:** `user_profiles` count from response is less than actual row count in DB.

### Pitfall 6: `interaction_counts` Key Type Mismatch

**What goes wrong:** `run_pipeline()` expects `dict[tuple[str,str], dict[str,int]]` keys as Python tuples. `fetch_all()` must build tuple keys, not list keys.
**Why it happens:** DB row columns are strings; building the pair key requires explicit `tuple()` or `(row["user_id_a"], row["user_id_b"])` syntax.
**How to avoid:** Use `pair_key = (row["user_id_a"], row["user_id_b"])` — Python tuple literal, not a list.
**Warning signs:** `TypeError: unhashable type: 'list'` in `compute_interaction_scores()`.

---

## Code Examples

Verified patterns from official sources:

### Full Table Read (supabase-py 2.28.0)

```python
# Source: supabase-py README + seed_db.py established pattern
response = supabase.table("user_profiles").select("*").execute()
rows = response.data  # list of dicts
```

### Filtered Update

```python
# Source: supabase-py 2.28.0 update docs
response = (
    supabase.table("map_coordinates")
    .update({"is_current": False})
    .eq("center_user_id", center_user_id)
    .eq("is_current", True)
    .execute()
)
```

### Bulk Insert

```python
# Source: supabase-py 2.28.0 insert docs
rows = [{"col1": v1, "col2": v2} for ...]
response = supabase.table("map_coordinates").insert(rows).execute()
inserted_count = len(response.data)
```

### UserProfile Construction from DB Row (with field mapping)

```python
# Source: CONTEXT.md decision + models/user.py field names
user = UserProfile(
    id=row["user_id"],
    interests=row["interests"] or [],
    languages=row["languages"] or [],
    city=row["location_city"],        # location_city → city
    state=row["location_state"],      # location_state → state
    education_level=row["education_level"],
    field_of_study=row["field_of_study"],
    occupation="",                    # not in DB; model requires it; empty string safe
    industry=row["industry"],
    age=row["age"],
)
```

### Canonical Pair Key Reconstruction

```python
# Source: CONTEXT.md + interactions table schema
# DB already enforces user_id_a < user_id_b — no re-sorting needed
pair_key = (row["user_id_a"], row["user_id_b"])  # tuple, not list
raw_interaction_counts[pair_key] = {
    "likes":    row["likes_count"],
    "comments": row["comments_count"],
    "dms":      row["dm_count"],
}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| No DB wiring (Phase 2 pure computation) | DB-connected via supabase-py client | Phase 3 | pipeline.py becomes the inner layer; data_fetcher/coord_writer are the DB boundary |
| Manual seed script invocation | Automated fetch in data_fetcher | Phase 3 | Algorithm reads live DB on every pipeline run instead of in-memory test data |

**Deprecated/outdated:**
- Nothing deprecated this phase — all Phase 2 modules remain unchanged.

---

## Open Questions

1. **Does `matching/similarity.py` break with `occupation=""`?**
   - What we know: `UserProfile.occupation` exists; DB `user_profiles` table has no `occupation` column; data_fetcher must pass `occupation=""`.
   - What's unclear: Whether `build_similarity_matrix()` in `matching/scoring.py` passes `occupation` to a similarity function that would fail on empty string.
   - Recommendation: Before implementing data_fetcher, check `backend/services/matching/scoring.py` and `similarity.py` to confirm `occupation` field behavior with empty string. If it causes issues, either (a) add `occupation: str = ""` as optional field with default or (b) verify the field is simply unused in the similarity computation. This is a low-risk check but worth confirming before running tests.

2. **Should the orchestrator function be in `__init__.py` or a new `pipeline_db.py`?**
   - What we know: Phase 4 scheduler and trigger endpoint need to import this function. Either location works.
   - Recommendation: Use `map_pipeline/__init__.py` for the orchestrator function (it's currently empty). This makes `from services.map_pipeline import run_pipeline_for_user` clean. Alternatively, `pipeline_db.py` is more explicit. Either is fine — planner's call.

3. **What happens on re-run for the same user when `map_coordinates` has existing rows?**
   - What we know: STORE-01 marks old rows `is_current=False` before inserting new ones. Old rows are retained (STORE-02).
   - What's unclear: Row count grows unboundedly with each pipeline run. This is expected and correct for Phase 3 — animation delta is a v2 concern.
   - Recommendation: No action needed in Phase 3. The two-step write pattern handles this correctly by design.

---

## Sources

### Primary (HIGH confidence)

- `/supabase/supabase-py` (Context7, 224 snippets) — `.table().select().execute()`, `.update().eq().execute()`, `.insert(list).execute()`, response.data structure
- Existing codebase `backend/scripts/seed_db.py` — supabase-py 2.28.0 usage patterns confirmed (table, upsert, select, on_conflict)
- Existing codebase `backend/config/supabase.py` — service role client singleton confirmed
- Existing codebase `backend/services/map_pipeline/pipeline.py` — `run_pipeline()` input/output contract read directly
- Existing codebase `backend/models/user.py` — `UserProfile` field names confirmed
- Existing codebase `backend/sql/setup_tables.sql` (via Phase 1 plan) — DB column names confirmed: `location_city`, `location_state`, `user_id`, `likes_count`, `comments_count`, `dm_count`
- `backend/venv`: supabase-py 2.28.0 confirmed installed

### Secondary (MEDIUM confidence)

- `.planning/phases/03-pipeline-integration/CONTEXT.md` — locked decisions confirmed by user
- `.planning/phases/01-database-foundation/01-01-SUMMARY.md` — table schemas and constraint details
- `.planning/phases/01-database-foundation/01-02-SUMMARY.md` — seed data structure, interaction pair patterns

### Tertiary (LOW confidence)

- Orchestrator location recommendation (`__init__.py` vs `pipeline_db.py`) — planner's discretion; no official guidance

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — supabase-py 2.28.0 confirmed installed; patterns verified from seed_db.py + Context7 docs
- Architecture: HIGH — CONTEXT.md is locked decisions; existing Phase 2 code read directly; DB schema confirmed from Phase 1
- Pitfalls: HIGH for DB pitfalls (verified from codebase); MEDIUM for `occupation` field gap (confirmed from model + DDL, but behavior in similarity.py needs one-time check)

**Research date:** 2026-02-22
**Valid until:** 2026-04-22 (supabase-py API is stable at 2.28.0; PostgREST query builder syntax is stable)
