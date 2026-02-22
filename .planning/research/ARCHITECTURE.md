# Architecture Research: SixDegrees People Map

**Domain:** t-SNE pipeline + batch scheduler + coordinate storage on FastAPI/Supabase
**Date:** 2026-02-22

---

## Component Map

```
FastAPI App
├── lifespan() → starts APScheduler on startup
├── GET /map/{user_id} → reads from map_coordinates table (fast, no compute)
└── POST /map/invalidate/{user_id} → triggers manual recompute (for testing)

APScheduler
└── CronTrigger per timezone → calls pipeline.run_for_timezone(tz)

Pipeline (backend/services/map_pipeline/)
├── data_fetcher.py      → fetch user_profiles + interactions from Supabase
├── similarity.py        → existing field-level similarity functions (keep)
├── scoring.py           → build NxN distance matrix (profile + interaction combined)
├── interaction.py       → NEW: normalize interaction counts, compute interaction score
├── tsne_projector.py    → NEW: run t-SNE on distance matrix → 2D coords
├── origin_translator.py → NEW: shift coords so requesting user is at (0,0)
├── tier_classifier.py   → existing KNN tier assignment (adapt)
└── coord_writer.py      → NEW: write to map_coordinates table (current + archive previous)

Supabase (PostgreSQL)
├── auth.users           → existing Supabase auth
├── user_profiles        → profile data for algorithm input
├── interactions         → interaction counts per user pair
└── map_coordinates      → precomputed (x, y, tier) per (center_user, other_user)
```

---

## Data Flow

```
1. Scheduler fires at 19:00 for timezone group "America/New_York"
   ↓
2. data_fetcher.fetch_profiles()
   → SELECT * FROM user_profiles WHERE timezone = 'America/New_York'
   → Returns: List[UserProfile]
   ↓
3. data_fetcher.fetch_interactions(user_ids)
   → SELECT * FROM interactions WHERE user_id_a IN (...) OR user_id_b IN (...)
   → Returns: Dict[(uid_a, uid_b), InteractionCounts]
   ↓
4. interaction.compute_interaction_scores(interactions, weights)
   → Normalize each interaction type independently (min-max per type)
   → Combine: score = sum(weight_i * normalized_count_i)
   → Returns: NxN interaction_score_matrix (values in [0,1])
   ↓
5. scoring.build_distance_matrix(profiles, interaction_scores, alpha, beta)
   → profile_distance = 1 - weighted_similarity(profiles)
   → combined_distance = alpha * profile_distance + beta * (1 - interaction_score)
   → Returns: NxN distance_matrix (values in [0,1])
   ↓
6. tsne_projector.project(distance_matrix, perplexity, random_state)
   → TSNE(metric='precomputed', init='random').fit_transform(distance_matrix)
   → Returns: (N, 2) array of raw coordinates
   ↓
7. For each user i in the group:
   a. origin_translator.translate(coords, center_idx=i)
      → shifted_coords = coords - coords[i]  (user i is now at (0,0))
   b. tier_classifier.assign_tiers(shifted_coords, center_idx=i)
      → Tier 1: 5 nearest, Tier 2: next 10, Tier 3: rest within threshold
   c. coord_writer.write(center_user_id=user_ids[i], coords=shifted_coords, tiers=tiers)
      → Archive previous: UPDATE map_coordinates SET is_current=false WHERE center_user_id=...
      → Insert new: INSERT INTO map_coordinates (center_user_id, other_user_id, x, y, tier, ...)
   ↓
8. GET /map/{user_id} reads precomputed rows — no computation at request time
   → SELECT * FROM map_coordinates WHERE center_user_id = ? AND is_current = true
   → Returns: JSON with coordinates array
```

---

## Build Order (Phase Dependencies)

```
Phase 1: Database Foundation
  → Create user_profiles, interactions, map_coordinates tables in Supabase
  → Write seed script (10-15 mock users + interactions)
  → Validate data reads correctly from Python

Phase 2: Core Algorithm (no DB dependency)
  → interaction.py: normalization + interaction score
  → scoring.py: extend to combine profile + interaction distance
  → tsne_projector.py: replace PCA with t-SNE (precomputed metric)
  → origin_translator.py: coord shift
  → Unit test with in-memory mock data (no Supabase needed)

Phase 3: Pipeline Integration
  → data_fetcher.py: reads real data from Supabase
  → coord_writer.py: writes results back to Supabase
  → Full end-to-end pipeline run (data → coords → stored)

Phase 4: API Endpoint + Scheduler
  → GET /map/{user_id} endpoint
  → APScheduler integration with FastAPI lifespan
  → Per-timezone cron trigger
  → Manual trigger endpoint for testing

Phase 5: Demo Deliverables
  → test_map.py: standalone matplotlib plot
  → people_map_demo.ipynb: interactive notebook with sensitivity demonstrations
```

---

## APScheduler + FastAPI Integration

**Key decision: AsyncIOScheduler, not BackgroundScheduler**

FastAPI uses asyncio. AsyncIOScheduler runs on the same event loop. BackgroundScheduler spins a thread — fine for simple cases but can cause issues with async DB clients.

```python
# backend/app.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from contextlib import asynccontextmanager
from services.map_pipeline.scheduler import schedule_timezone_jobs

scheduler = AsyncIOScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    schedule_timezone_jobs(scheduler)
    scheduler.start()
    yield
    scheduler.shutdown(wait=False)

app = FastAPI(lifespan=lifespan)
```

**Multi-worker concern**: If running multiple uvicorn workers, each worker starts its own scheduler, running the job N times. For this milestone (single worker), not an issue. Document as known limitation.

---

## Interaction Modularity Pattern

```python
# backend/config/algorithm.py
INTERACTION_WEIGHTS = {
    "likes_count": 0.5,
    "comments_count": 0.35,
    "dm_count": 0.15,
}

# Adding a new interaction type requires ONLY:
# 1. Add column to interactions table: ALTER TABLE interactions ADD COLUMN reaction_count INT DEFAULT 0;
# 2. Add weight: INTERACTION_WEIGHTS["reaction_count"] = 0.1 (and re-normalize others)
# 3. That's it — interaction.py reads weights dict, no code changes
```

```python
# backend/services/map_pipeline/interaction.py
def compute_interaction_scores(
    interactions: Dict[Tuple[str, str], Dict[str, int]],
    weights: Dict[str, float] = INTERACTION_WEIGHTS,
) -> np.ndarray:
    # Normalize each interaction type independently
    # Combine using weights dict
    # Returns NxN matrix
    ...
```

---

## Animation Readiness

The `is_current` boolean + keeping previous rows means:

```python
# Future animation system can query:
current = [r for r in rows if r.is_current]
previous = [r for r in rows if not r.is_current]  # most recent previous set
delta = {uid: (prev[uid] → current[uid]) for uid in all_users}
```

No additional schema work needed — the two-row pattern handles this.

---
*Research written: 2026-02-22*
