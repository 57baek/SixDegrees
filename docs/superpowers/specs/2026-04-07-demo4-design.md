# Demo-4 Backend: Design Spec

**Date:** 2026-04-07  
**Branch:** `ai`  
**Scope:** Advanced testing, full code quality audit, README, Playwright E2E validation

---

## Context

SixDegrees is a social networking platform with a FastAPI backend, Supabase (PostgreSQL) database, and Vue 3 frontend. The `ai` branch adds an embedding-based profile similarity feature using `all-MiniLM-L6-v2` (sentence-transformers). The backend has 110 passing tests across 19 test files.

Demo-4 requirements:
1. Fully integrated system (already done)
2. Advanced feature — embedding-based matching (already implemented)
3. Advanced testing — two methods, one on embedding feature, one on UMAP pipeline
4. Code quality — thorough audit, modularity, error handling, clarity
5. README — workflow, AI assistance, quality verification
6. Playwright E2E — live validation of all frontend + backend features

---

## Section 1: Advanced Testing

### 1A — Fuzz Testing via Hypothesis (embedding feature)

**File:** `backend/tests/test_embedder_property.py`

**Method:** Property-based / fuzz testing using the `hypothesis` library. Hypothesis generates arbitrary inputs automatically and checks that stated invariants hold for all of them. This satisfies the "fuzz testing" advanced testing requirement.

**Invariants to assert:**

| Function | Invariant |
|---|---|
| `cosine_sim(a, b)` | Always returns `float` in `[0.0, 1.0]`, never NaN |
| `cosine_sim(a, a)` | Always returns `1.0` for any non-zero vector |
| `cosine_sim(zeros, b)` | Always returns `0.0` |
| `build_profile_text(p)` | Never raises, always returns `str` |
| `build_profile_text(p)` | Empty interests + no bio always returns `""` |
| `embed_profiles(profiles)` | Shape always `(N, 384)`, no NaN, dtype float32 |
| `embed_profiles([empty_profile])` | Zero vector output |
| `get_top_matches(u, others)` | Each `similarity_score` always in `[0.0, 1.0]` |

**Dependencies to add:** `hypothesis`, `hypothesis[numpy]` to `requirements.txt`

**Evidence for demo:** Run with `pytest tests/test_embedder_property.py -v` — show Hypothesis generating hundreds of examples and all passing.

---

### 1B — Regression Testing (UMAP pipeline)

**Files:**
- `backend/tests/map/test_pipeline_regression.py`
- `backend/tests/fixtures/umap_regression_snapshot.npy` (committed)

**Method:** Deterministic snapshot regression. The UMAP projector uses `random_state=42`. Given a fixed synthetic input distance matrix, the output coordinates must be bit-for-bit reproducible. A committed `.npy` snapshot is the ground truth.

**Test structure:**

1. `test_snapshot_valid` — verify the committed snapshot is finite, correct shape, no NaN (sanity check)
2. `test_umap_regression` — build a fixed 20×20 synthetic distance matrix (seeded `np.random`), run `projector.project()`, compare to snapshot within `atol=1e-4`
3. `test_full_pipeline_regression` — run `distance.build_combined_distance()` on fixed `PipelineInput`, then `projector.project()`, compare shape and that diagonal is zero

**Snapshot regeneration:** Delete `tests/fixtures/umap_regression_snapshot.npy` and run `pytest tests/map/test_pipeline_regression.py::test_umap_regression --snapshot-update` (or a small helper script). Documented in a comment at the top of the test file.

**Evidence for demo:** Show the snapshot file, show the test passing, then deliberately change a constant in `projector.py` and show the test failing.

---

## Section 2: Code Quality Audit

### 2A — Dead code removal

| Item | File | Action |
|---|---|---|
| `/test-cors` debug endpoint | `app.py` | Delete |
| `Optional`, `List` imports (pre-3.10 style) | `routes/profile.py` | Replace with `str \| None`, `list[str] \| None` |
| Unused imports | All route/service files | Remove |
| httpx `app` shortcut deprecation warnings | All test files using `TestClient` | Fix to `WSGITransport` style |

### 2B — Coverage gaps to fill

Run `pytest --cov=. --cov-report=term-missing` to identify all uncovered lines. Priority targets:

| Module | Gap |
|---|---|
| `services/matching/scoring.py` | `build_similarity_matrix`, `apply_weights`, `similarity_to_distance` — no direct tests |
| `routes/profile.py` | `GET /profile` 404 path; interest normalization (dedup, lowercase, strip) |
| `routes/interactions.py` | Self-interaction 400 guard; all three interaction types (like, comment, dm) |
| `services/map/distance.py` | Branch coverage on edge cases |
| `services/map/ego.py` | Any uncovered branches |

**Target:** 90%+ line coverage.

### 2C — Code clarity pass

- Standardize `HTTPException` detail messages: sentence case, no trailing period, consistent phrasing across all routes
- Any function exceeding ~30 lines that has mixed responsibilities gets split or documented with inline comments
- `scripts/seed.py` — read and clean: remove dead code, clarify intent, consistent style
- Verify all type hints are correct and present on new/edited code
- `isort` pass on all files for import ordering

---

## Section 3: README

**File:** `README.md` at repo root

**Contents:**

### Major workflow and choices
- Two-path data flow: social features go directly to Supabase RPCs; map/match go through FastAPI
- UMAP pipeline stages: `fetcher → distance → projector → validation → writer → diagnostics`
- Embedding-based matching: `all-MiniLM-L6-v2` encodes `interests + bio` into 384-dim vectors; cosine similarity replaces Jaccard for the interests dimension
- Key constraints: single-worker deployment (APScheduler), private/public schema split, embedding fallback to Jaccard when `EMBEDDING_FIELDS=[]`

### How AI assisted development
- Claude Code (claude-sonnet-4-6) used throughout via Claude Code CLI
- Specific contributions: UMAP pipeline architecture, embedder design and test strategy, property-based test invariant design, code audit and cleanup
- Human review: all generated code reviewed before commit; test assertions manually verified against expected math

### How quality/correctness was verified
- 110+ unit and integration tests, all mocking Supabase (no live DB calls in CI)
- `pytest --cov` coverage report (90%+)
- Fuzz testing via Hypothesis: mathematical invariants on embedding functions verified across hundreds of generated inputs
- Regression snapshot test: UMAP pipeline output pinned to committed `.npy` snapshot, detects any geometry-breaking change
- Playwright E2E: live walkthrough of all features against real Supabase instance

---

## Section 4: Playwright End-to-End Validation

**Tool:** Playwright MCP (available in Claude Code session)  
**Target:** Frontend dev server on `:5173` + backend on `:8000`

**Prerequisites (human must start before this step):**
```bash
# Terminal 1
cd backend && source venv/bin/activate && uvicorn app:app --reload

# Terminal 2
cd frontend && npm run dev
```

**Test flow:**

1. Load app at `localhost:5173`
2. Sign up with a new account (email + password)
3. Complete onboarding — fill in nickname, interests, bio, location
4. Browse posts feed — verify posts load
5. Create a post — verify it appears
6. Like and comment on a post
7. Send a friend request to another user
8. Navigate to People Map — verify map renders with coordinates
9. Navigate to Match page — verify matches appear with similarity scores
10. Check browser console throughout for errors

**Output:**
- Screenshots saved to `demo/e2e_screenshots/` at each major step
- Explicit pass/fail report before anything is committed
- Any console errors or failed network requests flagged

---

## Implementation Order

1. Add `hypothesis` to `requirements.txt`
2. Write `tests/test_embedder_property.py`
3. Generate and commit `tests/fixtures/umap_regression_snapshot.npy`
4. Write `tests/map/test_pipeline_regression.py`
5. Run full coverage audit → fill gaps
6. Dead code removal + import cleanup + deprecation fixes
7. Code clarity pass (error messages, long functions, seed.py)
8. Write `README.md`
9. Run full test suite — confirm all pass, 90%+ coverage
10. Playwright E2E validation
