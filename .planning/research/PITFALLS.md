# Pitfalls Research: SixDegrees People Map

**Domain:** t-SNE pipeline + interaction normalization + APScheduler + social graph systems
**Date:** 2026-02-22

---

## Critical Pitfalls

### 1. t-SNE Non-Determinism — Map Rotates/Flips Between Runs

**The trap:** t-SNE with `random_state` still produces outputs that can be mirror-flipped or rotated relative to previous runs. With the same data and same random seed, results are reproducible — but change the data slightly (add a user, change an interaction), and the entire map can rotate 180° or mirror-flip. This makes the daily update visually chaotic even when the actual relationships barely changed.

**Warning signs:**
- Day 1 map shows User A to the right of center; Day 2 (minor data change) shows User A to the left
- In testing: identical input gives same output; but adding one new user reshuffles everyone

**Prevention:**
- Fix `random_state=42` in TSNE params — mandatory
- After t-SNE, apply Procrustes alignment: align today's raw coordinates to yesterday's using a rotation/reflection matrix before storing. This minimizes visual drift while preserving the relative structure.
- Store raw t-SNE coordinates before origin translation so Procrustes can be applied consistently
- For this milestone: fix random_state and document Procrustes as a known future improvement

**Phase:** Algorithm core (Phase 2) — document the limitation; Phase 4 (Polish) to implement Procrustes

---

### 2. t-SNE `metric='precomputed'` + Wrong `init` Parameter

**The trap:** `sklearn.manifold.TSNE` with `metric='precomputed'` requires `init='random'`. The default init is `'pca'` in newer sklearn versions — but PCA init is computed from input features, not from a distance matrix, causing a silent failure or crash.

**Warning signs:**
- ValueError: "PCA initialization is only supported with metric='euclidean'"
- Or: weird output where all points cluster at origin

**Prevention:**
- Always set `init='random'` when using `metric='precomputed'`
- In tests: verify that the input to TSNE is a valid distance matrix (symmetric, zeros on diagonal, values in [0,1])

**Phase:** Algorithm core (Phase 2) — validate in unit tests

---

### 3. Interaction Normalization Collapse — Superuser Problem

**The trap:** Min-max normalization across all pairs collapses when one user is hyper-active (e.g., a user with 10,000 likes while most pairs have 0-5). After normalization, everyone except the superuser has interaction scores near 0, effectively making interaction data meaningless.

**Warning signs:**
- In seed data: one user has interaction counts 100x higher than others
- After normalization: all non-superuser pairs have interaction_score ≈ 0.0

**Prevention:**
- Use percentile clipping before min-max: clip values at 95th percentile before normalizing
- Or use log normalization: `log(1 + count)` before min-max
- Recommended: `clipped_value = min(count, percentile_95_of_all_counts)`, then min-max
- Add an assertion in the pipeline: after normalization, check that the std dev of interaction scores is > 0.05; warn if collapsed

**Phase:** Interaction module (Phase 2)

---

### 4. APScheduler Double-Firing with Multiple Workers

**The trap:** If uvicorn is started with `--workers 2` (or any N > 1), each worker process starts its own APScheduler instance. The daily batch job fires N times simultaneously, causing N concurrent writes to the same map_coordinates rows.

**Warning signs:**
- In logs: see N instances of "Running map pipeline for timezone X" at the same time
- In DB: duplicate coordinate rows, or race condition on the `is_current` flag update

**Prevention:**
- For this milestone: always run with `uvicorn app:app --reload` (single worker) — document this constraint
- Longer term: use a database-backed job store (APScheduler + PostgreSQL job store) so only one worker fires
- Or: run scheduler in a separate standalone script, not embedded in FastAPI
- Add a `SELECT ... FOR UPDATE` lock in coord_writer to prevent concurrent writes for same center_user_id

**Phase:** Scheduler (Phase 4) — document single-worker constraint in README

---

### 5. Cold Start — New Users with No Interaction Data

**The trap:** A new user with zero interactions and a sparse profile gets a distance of ~0.5 from everyone (midpoint of the distance range). In t-SNE, this produces a user that appears "equidistant" from everyone in a diffuse cloud, rather than clustered near their actual similar users. Looks like a bug.

**Warning signs:**
- New user appears in a ring exactly equidistant from everyone
- User with no interests field populated gets placed oddly

**Prevention:**
- In profile similarity: treat missing fields as "unknown" — don't return 0 similarity, return a neutral value (0.5) so the user doesn't appear maximally distant
- In interaction scores: missing pair = 0.0 interaction score (already natural)
- Document the cold-start behavior in the demo notebook: "new users with no data appear at moderate distance — this is expected"

**Phase:** Data fetcher / similarity functions (Phase 2-3)

---

### 6. t-SNE Requires N ≥ perplexity*3 (Small Dataset Instability)

**The trap:** With only 10-15 mock users (demo scale), t-SNE with `perplexity=30` will fail or produce garbage. Perplexity must be less than N.

**Warning signs:**
- ValueError: "perplexity must be less than n_samples"
- Or: all points converge to a single location

**Prevention:**
- Set `perplexity = min(30, max(5, int(sqrt(N))))`
- For N=15: perplexity should be ~5-10
- Add a guard: `if N < 10: raise ValueError("Need at least 10 users to run t-SNE")`
- In tests: always use at least 10 seed users

**Phase:** t-SNE projector (Phase 2)

---

### 7. Origin Translation Breaks If Requesting User Is Missing from DB

**The trap:** `GET /map/{user_id}` translates coordinates so user_id is at (0,0). But if user_id has no profile in `user_profiles`, they aren't in the t-SNE result — and trying to look up their index in the coordinate array crashes.

**Warning signs:**
- KeyError or IndexError in origin_translator when user has no profile

**Prevention:**
- Validate user exists in `user_profiles` before running pipeline
- In `GET /map/{user_id}`: return 404 with message "User profile not found — please complete profile setup" if user_id isn't in map_coordinates
- Add user_id existence check at pipeline entry point

**Phase:** API endpoint + data fetcher (Phase 3-4)

---

### 8. Supabase Row-Level Security Blocks Backend Service Role

**The trap:** If RLS (Row Level Security) is enabled on `user_profiles` or `map_coordinates` without an explicit service role bypass, the Python backend using the service role key still gets permission denied.

**Warning signs:**
- Supabase returns empty results for queries that should return data
- No error raised — just an empty list

**Prevention:**
- Use the service role key in the backend (not anon key) — the service role bypasses RLS by default
- Verify in Supabase dashboard that `config/supabase.py` uses `SUPABASE_KEY` (service role), not the anon key
- When creating new tables, test a Python query immediately after creation to catch RLS issues early

**Phase:** Database setup (Phase 1)

---

## Quick Reference

| Pitfall | Severity | Phase |
|---------|----------|-------|
| t-SNE rotation/flip across runs | High | Phase 2 |
| Wrong `init` param with precomputed metric | High | Phase 2 |
| Interaction normalization collapse | Medium | Phase 2 |
| APScheduler multi-worker double-fire | Medium | Phase 4 |
| Cold start new users | Low | Phase 2-3 |
| t-SNE perplexity > N | High | Phase 2 |
| Origin translation on missing user | Medium | Phase 3-4 |
| Supabase RLS blocking service role | Medium | Phase 1 |

---
*Research written: 2026-02-22*
