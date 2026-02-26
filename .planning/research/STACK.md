# Stack Research

**Domain:** SixDegrees v2.0 global coordinate map engine (backend only)
**Researched:** 2026-02-26
**Confidence:** HIGH

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| `umap-learn` | `0.5.11` | Stage A global manifold embedding from profile feature vectors | UMAP operates directly on feature vectors (including `metric='cosine'`), avoids dense NxN precomputed distance matrices, and is better aligned with the v2 sparse-scaling requirement than current t-SNE-precomputed flow. |
| `scipy` | `1.17.1` | Sparse graph structures and numeric kernels for Stage B interaction refinement | `scipy.sparse`/`csgraph` gives efficient sparse adjacency operations for interaction edges (`E << N^2`) and keeps refinement in-process without adding infrastructure services. |
| `scikit-learn` | `1.8.0` | Feature preprocessing + controlled fallback manifold tooling | Current code already depends on sklearn; keeping it as shared preprocessing and utility layer minimizes migration risk. Official TSNE docs also confirm `max_iter` naming (post-1.5), reducing API drift risk in any fallback path. |
| `APScheduler` | `3.11.2` | Daily UTC global compute and timezone-local warm jobs | Existing scheduler architecture already uses APScheduler; 3.11 keeps compatibility with current `AsyncIOScheduler` + `CronTrigger(timezone=...)` model and preserves single-worker constraint. |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pynndescent` | `0.6.0` | Approximate nearest-neighbor graph build used by UMAP internals | Pin explicitly to stabilize neighbor-graph behavior across deploys and avoid hidden transitive version shifts. |
| `prometheus-fastapi-instrumentator` | `7.1.0` | Request/job metrics endpoint for map compute and map serving | Add when enabling operational SLOs for compute duration, job failures, and `/map` latency budgets. |
| `python-json-logger` | `4.0.0` | Structured JSON logs for pipeline/audit events | Use for run-scoped correlation fields (`run_id`, `version_date`, `user_count`, `edge_count`) so each daily map build is auditable. |
| `hypothesis` | `6.151.9` | Property-based validation for algorithm invariants | Use in backend tests for invariants like symmetry, bounded movement clamps, deterministic seeds, and ego-map origin translation. |
| `pytest-benchmark` | `5.2.3` | Performance regression guardrails in CI/local runs | Use to enforce upper bounds for global job runtime and ego-map query-time complexity as user graph grows. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| `pytest` (`>=9.0`) | Test orchestration for deterministic + property/perf suites | Keep existing harness; add marker groups for `algorithm`, `contract`, and `performance`. |
| Prometheus + Grafana (deployment side) | Time-series monitoring for pipeline health | No app architecture rewrite required; scrape `/metrics` from existing FastAPI service. |

## Concrete Integration Points (Current Backend)

- `backend/services/map_pipeline/tsne_projector.py`: replace precomputed-distance t-SNE stage with a UMAP-based projector over profile vectors.
- `backend/services/map_pipeline/pipeline.py`: update stage contract from dense NxN matrix flow to `(features -> embedding -> sparse refinement)`.
- `backend/services/map_pipeline/interaction.py`: keep weighted interactions logic but emit sparse edge list/CSR structure for Stage B refinement instead of forcing dense matrix materialization.
- `backend/services/map_pipeline/data_fetcher.py`: continue secured Supabase RPC reads; extend payload shaping for vectorization/refinement inputs without touching `profiles` schema.
- `backend/services/map_pipeline/scheduler.py`: keep one daily global compute trigger (UTC) and add metrics/log instrumentation around each run and timezone warm job.
- `backend/app.py`: register Prometheus instrumentation (`/metrics`) and JSON logging formatter at startup.
- `backend/tests/map_pipeline/`: add Hypothesis properties + benchmark tests for stability/performance gates required by v2 validation criteria.

## Installation

```bash
# Core v2 compute stack additions
cd backend && pip install "umap-learn==0.5.11" "scipy==1.17.1" "scikit-learn==1.8.0" "pynndescent==0.6.0"

# Validation + observability additions
cd backend && pip install "prometheus-fastapi-instrumentator==7.1.0" "python-json-logger==4.0.0" "hypothesis==6.151.9" "pytest-benchmark==5.2.3"
```

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| UMAP (`umap-learn`) | t-SNE with precomputed full distance matrix | Only for very small offline experiments where NxN memory cost is acceptable; not for v2 production global run. |
| SciPy sparse refinement | NetworkX-centric refinement loop | Use NetworkX only for debugging/visualization; not for production compute path where sparse numeric kernels are required. |
| Prometheus instrumentator | OpenTelemetry FastAPI instrumentation package | Revisit when OpenTelemetry FastAPI instrumentation exits beta and full distributed tracing is required. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| Full NxN precomputed distance matrix in production pipeline | Violates v2 scalability intent (`O(N^2)` memory/compute pressure) and conflicts with locked milestone notes | UMAP on feature vectors + sparse interaction refinement (`O(N + E)`-oriented path) |
| Frontend map protocol/library changes | Hard constraint: no frontend code changes for this milestone | Keep response shape backward-compatible and evolve backend internals only |
| Schema changes to `profiles` or `pending_requests` | Explicitly locked out-of-scope constraints in milestone context | Derive needed features from existing `profiles` fields and interactions data |
| Replacing APScheduler with Celery/Redis in v2 | Adds infra surface area and migration risk without being required for current single-worker architecture | Keep APScheduler 3.11; add stronger validation, instrumentation, and run controls |

## Stack Patterns by Variant

**If global user count is in low-to-mid tens of thousands:**
- Use in-process UMAP + SciPy sparse refinement in one daily batch.
- Because this preserves current deployment simplicity while removing NxN bottlenecks.

**If global user count grows toward sustained six-figure+ daily recomputes:**
- Keep same algorithmic stack but split compute into partitioned batches and merge with continuity constraints.
- Because this scales operationally without violating frontend/schema constraints or changing map-serving contract.

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| `umap-learn==0.5.11` | `pynndescent==0.6.0`, `scikit-learn==1.8.0`, `scipy==1.17.1` | UMAP docs and internals rely on NN-descent and sklearn ecosystem; pin as a set for deterministic embeddings. |
| `prometheus-fastapi-instrumentator==7.1.0` | FastAPI app startup/lifespan pattern | Supports straightforward `instrument(app).expose(app)` integration in existing app lifecycle. |
| `hypothesis==6.151.9` | `pytest` backend suite | Native pytest integration for property-based tests; no framework migration needed. |

## Sources

- Context7 `/websites/umap-learn_readthedocs_io_en` - UMAP feature-vector usage, cosine metric, reproducibility, sparse/NN graph behavior (HIGH)
- Context7 `/trallnag/prometheus-fastapi-instrumentator` - FastAPI instrumentation and `/metrics` exposure pattern (HIGH)
- Official sklearn TSNE docs: `https://scikit-learn.org/stable/modules/generated/sklearn.manifold.TSNE.html` - `metric='precomputed'` behavior and `n_iter` -> `max_iter` rename in 1.5 (HIGH)
- Official APScheduler docs: `https://apscheduler.readthedocs.io/en/3.x/modules/triggers/cron.html` - timezone-aware `CronTrigger` behavior and DST caveats (HIGH)
- Official SciPy sparse docs: `https://docs.scipy.org/doc/scipy/reference/sparse.html` - sparse array/matrix guidance for efficient graph computation (HIGH)
- Official UMAP parameter docs: `https://umap-learn.readthedocs.io/en/latest/parameters.html` - `n_neighbors`, `min_dist`, `metric` tradeoffs (HIGH)
- PyPI JSON APIs (queried 2026-02-26) for version baselines: `umap-learn`, `scipy`, `pynndescent`, `scikit-learn`, `apscheduler`, `prometheus-fastapi-instrumentator`, `hypothesis`, `python-json-logger`, `pytest-benchmark` (MEDIUM: packaging metadata source)

---
*Stack research for: SixDegrees milestone v2.0 global coordinate map engine*
*Researched: 2026-02-26*
