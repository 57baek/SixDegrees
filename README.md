# SixDegrees

A social networking platform centered on a live, interactive People Map that places users in 2D space based on profile similarity and interaction history.

---

## Architecture Overview

### Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI + APScheduler |
| Database | Supabase (PostgreSQL) |
| Frontend | Vue 3 + Vite |
| Auth | Supabase JWT (validated server-side) |
| Map engine | UMAP (umap-learn 0.5.11) |
| Matching | sentence-transformers (all-MiniLM-L6-v2) |

### Two-path data flow

1. **Social features** (posts, likes, comments, friend requests, profile CRUD): the frontend calls Supabase RPCs directly — FastAPI is bypassed entirely for these.
2. **Map + matching** (coordinates, similarity scores): the frontend calls FastAPI REST endpoints (`GET /map/{userId}`, `POST /map/trigger/{userId}`, `GET /match`), which query Supabase internally and return computed results.

### UMAP pipeline

The People Map is built by a scheduled background pipeline:

```
fetcher → distance → projector → validation → writer → diagnostics
```

- **fetcher**: pulls all profiles and interaction rows from Supabase
- **distance**: builds an N×N combined distance matrix
  - Profile distance: `build_similarity_matrix` (per-field scores) → `apply_weights` → `similarity_to_distance`
  - Interaction distance: normalized likes + comments + DMs, inverted
  - Combined: `ALPHA × profile_dist + BETA × interaction_dist`
- **projector**: runs UMAP with `metric="precomputed"` and `random_state=42`
- **validation**: checks output for NaN / Inf / shape errors
- **writer**: clips coordinate delta for position stability, upserts `user_positions`
- **diagnostics**: records run status and metrics to `pipeline_runs`

### Embedding-based matching

`GET /match` ranks all other users by a weighted similarity score:

- **Interests** (40% weight): encoded with `all-MiniLM-L6-v2` into 384-dim vectors; cosine similarity replaces Jaccard when `EMBEDDING_FIELDS` is non-empty
- **Location** (20%), **Languages** (15%), **Education** (10%), **Industry** (10%), **Age** (5%): computed with tiered categorical and inverse-distance functions

Fallback: when `EMBEDDING_FIELDS=[]`, Jaccard similarity is used for interests instead of embeddings.

### Key constraints

- **Single-worker only**: APScheduler fires N times with N Uvicorn workers — always run with `uvicorn app:app --reload` (no `--workers N`)
- **Profile table**: `public.profiles` is a writable view over `private.profiles`; backend always uses `sb.table("profiles")`
- **Embedder singleton**: `_model` is lazy-loaded on first call; not thread-safe (safe under single-worker deployment)

---

## Running the Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # set SUPABASE_URL and SUPABASE_KEY (service-role key)
uvicorn app:app --reload
```

## Running Tests

```bash
cd backend
source venv/bin/activate
python -m pytest -q                          # all tests
python -m pytest --cov=. --cov-report=term-missing  # with coverage
python -m pytest tests/test_embedder_property.py -v  # fuzz tests
```

---

## How AI Assisted Development

This project was developed with [Claude Code](https://claude.ai/code) (claude-sonnet-4-6) used throughout via the Claude Code CLI. Three specific ways AI assistance made a measurable difference:

### 1. Codebase onboarding and understanding

Claude Code reads and reasons across entire codebases. When working with unfamiliar code, you can ask Claude to read a module and explain how it fits into the broader system — which files it depends on, what data it receives, what it returns. This replaces manual execution tracing and is particularly effective when joining a project mid-development or reading a teammate's code.

In this project, Claude read the full UMAP pipeline (`fetcher → distance → projector → validation → writer`) and explained the data contracts between each stage before any changes were made. This replaced what would normally be 30–60 minutes of tracing source files.

### 2. Writing repetitive tests

Tests should not contain logic — they should be simple, direct, binary checks: given this input, assert this output. This makes test writing repetitive by design. That repetition is exactly what AI does well.

Claude wrote the majority of the test suite in this project:
- 22 map pipeline tests (fetcher, distance, projector, validation, writer, ego, pipeline, scheduler, diagnostics)
- Route endpoint tests for profile, match, map, interactions
- Similarity function edge case tests
- Contract tests for all API request/response shapes

This freed up development time for decisions that actually required judgment: what invariants to assert, what edge cases matter, and what coverage gaps to fill.

### 3. Property-based test design

Designing Hypothesis fuzz tests requires identifying mathematical invariants — properties that must hold for *all* inputs, not just a handful of examples. Claude helped translate informal correctness requirements into precise, testable invariants, and also caught a test design error: the strategy was generating vectors of independent random shapes, which would cause a shape mismatch error instead of testing the actual function. The fix required a composite strategy that ties both vectors to the same randomly chosen dimension.

All generated code was reviewed before commit. Test assertions were manually verified against expected math. Architectural decisions (UMAP pipeline structure, embedding fallback, interaction pair canonical ordering) were made by the developers and implemented with AI assistance.

---

## Quality Verification

### Test suite

138 unit and integration tests across 22 test files. All Supabase calls are mocked — no live DB calls in the test suite.

```bash
python -m pytest -q   # 138 passed
```

### Coverage

97% line coverage across all backend modules.

```bash
python -m pytest --cov=. --cov-report=term-missing
```

### Fuzz testing (Hypothesis)

Property-based tests in `tests/test_embedder_property.py` verify mathematical invariants on embedding functions across hundreds of auto-generated inputs. Hypothesis shrinks failing examples to minimal counterexamples automatically.

```bash
pytest tests/test_embedder_property.py -v
```

Invariants tested:
- `cosine_sim` always returns `[0.0, 1.0]`, never NaN
- `cosine_sim(v, v) == 1.0` for all non-zero vectors
- `build_profile_text` never raises, always returns `str`
- `embed_profiles` always returns shape `(N, 384)`, no NaN, dtype float32
- `get_top_matches` scores always in `[0.0, 1.0]`

### Regression testing (UMAP)

Snapshot regression in `tests/map/test_pipeline_regression.py` pins UMAP output to a committed `.npy` file. The test fails if any geometry-breaking change is introduced to the pipeline.

```bash
pytest tests/map/test_pipeline_regression.py -v
```

To regenerate after a `umap-learn` upgrade:
```bash
cd backend && python tests/fixtures/generate_snapshot.py
```
