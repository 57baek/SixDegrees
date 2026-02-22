# Stack Research: SixDegrees People Map

**Domain:** t-SNE dimensionality reduction + APScheduler batch jobs on FastAPI/Supabase
**Date:** 2026-02-22
**Milestone:** subsequent (adding to existing Python/FastAPI/Supabase stack)

---

## Summary

The existing stack (Python/FastAPI, scikit-learn, Supabase) already contains everything needed. Three new components are required: t-SNE (already in scikit-learn), APScheduler for batch scheduling, and a coordinate storage pattern in Supabase.

---

## t-SNE: sklearn.manifold.TSNE vs openTSNE

### Recommendation: **sklearn.manifold.TSNE** (already installed, sufficient for this scale)

| Library | Version | Verdict |
|---------|---------|---------|
| sklearn TSNE | scikit-learn ≥1.4 (already in requirements) | ✓ Use this |
| openTSNE | 1.0.2 | Only needed if N > 5000 users; faster but adds a dep |
| MulticoreTSNE | unmaintained | ✗ Avoid |

**Why sklearn is sufficient:**
- N ≤ ~2000 users: sklearn TSNE runs in seconds to minutes
- N > 5000: openTSNE (uses FFT approximation) would be faster
- This milestone is demo/prototype scale — sklearn is the right choice
- openTSNE uses the same API pattern, so migration later is trivial

**Critical sklearn TSNE parameters:**
```python
from sklearn.manifold import TSNE

tsne = TSNE(
    n_components=2,
    metric='precomputed',    # CRITICAL: we pass a distance matrix, not raw features
    init='random',           # NOT 'pca' — pca init fails with precomputed metric
    perplexity=30,           # Rule of thumb: sqrt(N), min 5, max N/3
    n_iter=1000,
    random_state=42,         # CRITICAL for reproducibility — see Pitfalls
    method='exact',          # 'barnes_hut' requires Euclidean space, not precomputed
)
coords = tsne.fit_transform(distance_matrix)  # shape: (N, 2)
```

**Confidence: High** — sklearn TSNE docs explicitly support precomputed distance matrices.

---

## APScheduler

### Recommendation: **APScheduler 3.x** (not 4.x — breaking changes, less stable)

```
apscheduler==3.10.4
```

**Why 3.x not 4.x:**
- APScheduler 4.0 was a full rewrite with async-first design
- As of 2026, 4.x is still maturing; 3.x is battle-tested and well-documented
- 3.x has synchronous and async job stores; simpler for a daily batch job

**FastAPI integration pattern (startup lifespan):**
```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from contextlib import asynccontextmanager

scheduler = AsyncIOScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.start()
    yield
    scheduler.shutdown()

app = FastAPI(lifespan=lifespan)
```

**Timezone scheduling — per-timezone trigger:**
```python
from apscheduler.triggers.cron import CronTrigger
import pytz

# Schedule job at 19:00 for each timezone group
for tz_name in unique_timezones:
    scheduler.add_job(
        run_pipeline_for_timezone,
        CronTrigger(hour=19, minute=0, timezone=pytz.timezone(tz_name)),
        args=[tz_name],
        id=f"map_update_{tz_name}",
        replace_existing=True,
    )
```

**Required packages:**
```
apscheduler==3.10.4
pytz>=2024.1
```

**Confidence: High** — APScheduler 3.x + FastAPI lifespan is a well-established pattern.

---

## Supabase Coordinate Storage

### Pattern: Two-row approach (current + previous)

The `map_coordinates` table should store both current and previous coordinates to enable animation deltas. Two approaches:

**Option A: Single table with `version` column (Recommended)**
```sql
CREATE TABLE map_coordinates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    center_user_id UUID NOT NULL REFERENCES auth.users(id),
    other_user_id UUID NOT NULL REFERENCES auth.users(id),
    x FLOAT NOT NULL,
    y FLOAT NOT NULL,
    tier INTEGER NOT NULL CHECK (tier IN (1, 2, 3)),
    computed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    is_current BOOLEAN NOT NULL DEFAULT true
);

CREATE INDEX idx_map_coordinates_center_current
    ON map_coordinates(center_user_id, is_current)
    WHERE is_current = true;
```

**Write pattern (batch update):**
1. Mark all current rows for center_user_id as `is_current = false`
2. Insert new rows with `is_current = true`
3. (Optional) Delete rows older than N days

**Read pattern (API):**
```python
# Fetch current map
rows = supabase.table("map_coordinates")\
    .select("other_user_id, x, y, tier")\
    .eq("center_user_id", user_id)\
    .eq("is_current", True)\
    .execute()

# Fetch animation delta (current + previous)
rows = supabase.table("map_coordinates")\
    .select("other_user_id, x, y, tier, computed_at, is_current")\
    .eq("center_user_id", user_id)\
    .order("computed_at", desc=True)\
    .limit(N * 2)  # current + one previous set
    .execute()
```

**Confidence: High** — Standard pattern for time-versioned coordinate tables.

---

## User Profiles Table

Supabase `user_profiles` table (extends auth.users):
```sql
CREATE TABLE user_profiles (
    user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    display_name TEXT,
    interests TEXT[] DEFAULT '{}',
    location_city TEXT,
    location_state TEXT,
    age INTEGER,
    languages TEXT[] DEFAULT '{}',
    field_of_study TEXT,
    industry TEXT,
    education_level TEXT CHECK (education_level IN ('bachelor', 'master', 'phd', 'other')),
    timezone TEXT DEFAULT 'UTC',  -- CRITICAL for batch scheduler
    updated_at TIMESTAMPTZ DEFAULT now()
);
```

---

## What NOT to Use

| Approach | Why Not |
|----------|---------|
| Redis + Celery | Overkill for daily batch; adds infra complexity; not needed at this scale |
| Celery Beat | Same — adds broker dependency |
| APScheduler 4.x | Unstable API, less documentation, breaking changes from 3.x |
| openTSNE (for now) | Only needed at N > 5000; adds dependency without benefit at demo scale |
| barnes_hut TSNE | Requires Euclidean input space, not precomputed distance matrix |
| PCA init for TSNE | Incompatible with `metric='precomputed'` — will crash |
| Separate scheduler process | Adds operational complexity; APScheduler embedded in FastAPI is cleaner for this scale |

---

## Dependency Updates Needed

Add to `backend/requirements.txt`:
```
apscheduler==3.10.4
pytz>=2024.1
```

Remove from `backend/requirements.txt` (unused):
```
sqlalchemy==2.0.25
psycopg2-binary==2.9.9
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
```

---
*Research written: 2026-02-22*
