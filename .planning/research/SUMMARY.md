# Research Summary: SixDegrees People Map

**Date:** 2026-02-22
**Milestone:** Backend algorithm pipeline — t-SNE people map with interaction data + batch scheduler

---

## Stack

**No new frameworks needed.** The existing stack (scikit-learn, FastAPI, Supabase) covers everything.

New dependencies to add:
- `apscheduler==3.10.4` — batch job scheduler
- `pytz>=2024.1` — timezone-aware scheduling

Use `sklearn.manifold.TSNE` (already installed via scikit-learn ≥1.4) with:
- `metric='precomputed'` (we pass a distance matrix)
- `init='random'` (required with precomputed metric — NOT 'pca')
- `random_state=42` (required for reproducibility)
- `perplexity = min(30, max(5, int(sqrt(N))))` (guard against small N)

For APScheduler: use `AsyncIOScheduler` (not `BackgroundScheduler`) with FastAPI's `lifespan` context. Run single-worker uvicorn only — multi-worker causes double-firing.

---

## Architecture

**5-module pipeline** in `backend/services/map_pipeline/`:

```
data_fetcher.py  →  scoring.py  →  tsne_projector.py  →  origin_translator.py  →  coord_writer.py
                        ↑
                 interaction.py (feeds into scoring)
```

**Build order must follow data dependencies:**
1. Database tables + seed data (user_profiles, interactions, map_coordinates)
2. Core algorithm modules (interaction scoring, combined distance matrix, t-SNE, origin translation)
3. Pipeline integration (data fetcher reads DB, coord writer writes DB)
4. API endpoint + APScheduler (serve precomputed results, schedule daily batch)
5. Demo deliverables (test_map.py + Jupyter notebook)

**Coordinate storage:** Two rows per (center_user, other_user) pair — current + previous — via `is_current` boolean flag. Enables future animation delta without schema changes.

---

## Table Stakes for Demo

- Scatter plot with labeled dots, colored by tier (3 colors)
- Demonstrable sensitivity: changing seed data → visible movement of dots
- Runs with single command against real Supabase instance
- At least 10 users (minimum for t-SNE stability)

---

## Critical Pitfalls to Avoid

### 1. t-SNE rotation/flip (HIGH risk)
Fix `random_state=42`. Accept that large data changes may rotate the map — document Procrustes alignment as future improvement.

### 2. Wrong t-SNE init parameter (HIGH risk)
`metric='precomputed'` REQUIRES `init='random'`. Setting `init='pca'` will crash or produce garbage.

### 3. Interaction normalization collapse (MEDIUM risk)
Clip at 95th percentile before min-max normalization. One superuser with 1000× more activity than others will collapse everyone else's scores to ~0.

### 4. Perplexity > N crash (HIGH risk)
Always compute: `perplexity = min(30, max(5, int(sqrt(N))))`. Fail fast if N < 10.

### 5. APScheduler multi-worker (MEDIUM risk)
Document clearly: run with single uvicorn worker only. Multiple workers = multiple scheduler instances = jobs fire N times.

### 6. Supabase RLS (MEDIUM risk)
Verify backend uses service role key. Test DB reads immediately after creating new tables.

---

## Interaction Modularity Pattern

Use a dict-driven weight config — adding a new interaction type requires:
1. One new column in `interactions` table
2. One new entry in `INTERACTION_WEIGHTS` dict
3. Zero logic changes

```python
INTERACTION_WEIGHTS = {
    "likes_count": 0.5,
    "comments_count": 0.35,
    "dm_count": 0.15,
}
```

---

## Distance Formula

```
distance(i, j) = α × profile_distance(i, j) + β × (1 - interaction_score(i, j))
```

Default: `α=0.6, β=0.4`. Store in `backend/config/algorithm.py`.

Profile distance = 1 - weighted_similarity (existing weights kept: interests 35%, location 20%, etc.)
Interaction score = weighted sum of normalized interaction counts (min-max clipped at 95th percentile)

---
*Summary written: 2026-02-22*
