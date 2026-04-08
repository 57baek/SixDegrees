# Embedding-Based Profile Similarity — Design Spec

**Date:** 2026-03-31
**Branch:** ai
**Status:** Approved

---

## Problem

The current profile similarity system uses hand-crafted per-field functions (Jaccard, tiered categorical, inverse-age distance). The weakest link is the `interests` field: Jaccard on stemmed tokens gives 0 similarity between semantically related interests like `"hiking"` and `"trail running"`. The `bio` field is completely unused in matching.

---

## Goal

Replace the Jaccard-based `interests` score with a sentence-transformer embedding + cosine similarity that captures semantic meaning. Fold `bio` into the same embedding. Keep all other fields (location, languages, education, industry, age) as hand-crafted scores. Make the split between embedding fields and hand-crafted fields configurable via `settings.py`.

---

## Approach

**Option A — Drop-in replacement** (chosen): Replace only the `interests` Jaccard score in `_profile_similarity()` with `cosine_sim(embed(interests + bio))`. One new file, minimal changes to `scoring.py`. No new abstractions, no A/B complexity.

---

## Design

### 1. Config (`config/settings.py`)

Two new constants added:

```python
# Fields whose similarity is computed via sentence-transformer embeddings.
# Replaces hand-crafted counterparts in the weighted profile score.
# Set to [] to disable embeddings entirely and fall back to hand-crafted methods.
EMBEDDING_FIELDS: list[str] = ["interests", "bio"]

# Sentence-transformers model — downloads once on first run (~90MB)
EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
```

`EMBEDDING_FIELDS` is the single control surface. A developer edits this before deploy to change which fields participate in semantic embedding. No logic changes needed.

---

### 2. New file: `services/matching/embedder.py`

Responsibilities: model lifecycle + text preparation + batch embedding.

```
build_profile_text(profile: UserProfile) -> str
    Concatenate EMBEDDING_FIELDS values into a single string.
    Reads EMBEDDING_FIELDS from config.settings at call time (dynamic — tests can patch it).

    Generic field joining rules (applies to any field in EMBEDDING_FIELDS):
      - list[str] fields: space-joined into a single string token
      - str fields: used as-is
      - None or empty list: field is skipped entirely (no separator emitted)
    Non-empty field parts are joined with ". " between them.
    If all fields are missing/None/empty → returns "".

    Examples for EMBEDDING_FIELDS = ["interests", "bio"]:
      interests=["hiking", "trail running"], bio="I love the outdoors"
        → "hiking trail running. I love the outdoors"
      interests=["hiking"], bio=None
        → "hiking"
      interests=[], bio="I love the outdoors"
        → "I love the outdoors"
      interests=[], bio=None
        → ""

    Example for EMBEDDING_FIELDS = ["interests", "bio", "occupation"]:
      interests=["hiking"], bio="I love the outdoors", occupation="engineer"
        → "hiking. I love the outdoors. engineer"
      interests=[], bio=None, occupation="engineer"
        → "engineer"

embed_profiles(profiles: list[UserProfile]) -> np.ndarray
    Batch encode all profiles in one model.encode() call.
    Returns shape (N, 384) — one 384-dim vector per profile.
    Precondition: profile IDs in the input list must be unique.
    Profiles where build_profile_text() returns "" receive np.zeros(384) —
    do NOT pass empty string to model.encode() (model output on empty tokens
    is undefined and implementation-specific). The zero vector is inserted
    directly without calling the model.
    Non-empty profiles are encoded in a single batch call for efficiency.
```

**Cosine similarity helper** (also in `embedder.py`):

```
cosine_sim(a: np.ndarray, b: np.ndarray) -> float
    Returns cosine similarity in [0, 1].
    If either vector is all-zeros (np.linalg.norm == 0), returns 0.0 directly
    without computing the dot product — avoids division-by-zero / nan.
    Raw cosine output is in [-1, 1]; clip to [0, 1] before returning
    (sentence-transformer embeddings are non-negative in practice, but clip
    defensively).
```

**Model lifecycle** — loaded **lazily**, not at module import. A module-level `_model` variable initialized to `None` is populated on first call to `embed_profiles()` via a `_get_model()` helper. This prevents the model from loading during tests when `embed_profiles` is mocked, and avoids a 90MB download at import time.

```python
_model = None  # not thread-safe; safe under single-worker deployment

def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBEDDING_MODEL)
    return _model
```

Note: `_get_model()` is not thread-safe. This is acceptable — the project runs single-worker Uvicorn by design. Do not add locking.

---

### 3. Changes to `scoring.py`

The following functions change: `_similarity_vector()`, `_profile_similarity()`, `get_top_matches()`, and `build_similarity_matrix()`. `apply_weights()` and `similarity_to_distance()` are untouched.

**Import style** — `scoring.py` imports from `config.settings` and `embedder.py` directly:
```python
from config.settings import EMBEDDING_FIELDS, PROFILE_WEIGHTS
from services.matching.embedder import embed_profiles, cosine_sim
```
Test patches must use the re-bound names in `scoring.py`'s namespace:
- `patch("services.matching.scoring.EMBEDDING_FIELDS", ...)`
- `patch("services.matching.scoring.embed_profiles", ...)`

**`get_top_matches(current_user, all_users, top_n)`**: `all_users` must NOT include `current_user` (existing contract, unchanged). Calls `embed_profiles(all_users + [current_user])` once upfront — input list has unique IDs by existing contract. Builds `embeddings: dict[str, np.ndarray]` keyed by user ID, passes it into `_profile_similarity()`.

**`_profile_similarity(u1, u2, embeddings: dict[str, np.ndarray])`**: gains `embeddings` parameter. Conditionally replaces `jaccard(u1.interests, u2.interests, stem=True)` based on `EMBEDDING_FIELDS`:

```python
if "interests" in EMBEDDING_FIELDS or "bio" in EMBEDDING_FIELDS:
    text_score = cosine_sim(embeddings[u1.id], embeddings[u2.id])
else:
    text_score = jaccard(u1.interests, u2.interests, stem=True)
```

When `EMBEDDING_FIELDS = []`, the condition is false and Jaccard is used — no change in behaviour. The score occupies the same 40% weight slot.

**`_similarity_vector(u1, u2, embeddings: dict[str, np.ndarray])`**: gains `embeddings` parameter. Same conditional replacement as `_profile_similarity()` for the interests dimension (index 0). This is critical — `_similarity_vector()` feeds `build_similarity_matrix()` which feeds the UMAP pipeline. Both the `/match` endpoint and the UMAP pipeline must use the same scoring method or positions and match scores will diverge.

**`build_similarity_matrix(users, embeddings: dict[str, np.ndarray] | None = None)`**: gains an optional `embeddings` parameter (default `None`). If `None`, calls `embed_profiles(users)` internally and builds the dict as `{users[i].id: embedding_rows[i] for i in range(len(users))}` before passing it to `_similarity_vector()`. If provided, uses the pre-computed dict as-is. This keeps `distance.py` unchanged — `build_combined_distance()` in `distance.py` calls `build_similarity_matrix(profiles)` with no embeddings argument, and the function handles embedding internally. `pipeline.py` is also unchanged (it calls `build_combined_distance()`, not `build_similarity_matrix()` directly).

The `interests` weight slot (40%) now represents `interests + bio` semantic similarity when `EMBEDDING_FIELDS` contains either field.

---

### 4. Error Handling & Edge Cases

| Case | Behaviour |
|------|-----------|
| Profile has no bio, no interests | `build_profile_text()` returns `""`. `embed_profiles()` inserts `np.zeros(384)` directly — does not call model. `cosine_sim()` receives a zero vector, returns `0.0`. No assumed similarity. |
| One user has content, other has none | One vector is zeros. `cosine_sim()` returns `0.0`. |
| Both users have empty profiles | Both vectors are zeros. `cosine_sim()` short-circuits to `0.0` (zero-norm guard). |
| Model fails to load | `SentenceTransformer()` raises on first call to `embed_profiles()` (first pipeline run). Error propagates up, pipeline fails loudly, `diagnostics.py` records the failure. No silent fallback to Jaccard. |
| `EMBEDDING_FIELDS = []` | `_profile_similarity()` and `_similarity_vector()` fall back to Jaccard for interests. `embed_profiles()` is never called. Model is never loaded. |

---

### 5. Tests

**New file: `tests/test_embedder.py`** — tests `embedder.py` directly; real model required for embedding tests (marks as integration or installs `sentence-transformers` in CI):
- `test_build_profile_text_full` — interests + bio → correct concatenated string
- `test_build_profile_text_interests_only` — bio=None → no trailing separator
- `test_build_profile_text_bio_only` — patch `EMBEDDING_FIELDS = ["bio"]`, interests field absent → bio text only, no leading separator
- `test_build_profile_text_empty` — no interests, no bio → `""`, no crash
- `test_embed_profiles_shape` — N profiles → output shape `(N, 384)` (uses real model)
- `test_embed_profiles_identical` — same profile twice → cosine sim = 1.0 (uses real model)
- `test_cosine_sim_zero_vector` — one or both zero vectors → returns `0.0`, no nan/crash
- `test_cosine_sim_identical` — same non-zero vector → returns `1.0`

**Extended: `tests/test_match.py`** — mocks `embed_profiles` to avoid model load:
- `test_embedding_fields_config` — patch `services.matching.scoring.EMBEDDING_FIELDS = []` → scores match Jaccard baseline
- `test_semantic_similarity` — mock embeddings for "hiking" and "trail running" with high cosine sim → match score higher than Jaccard would produce

All tests in `test_match.py` mock `embed_profiles` via `patch("services.matching.scoring.embed_profiles", ...)` to avoid loading the model in CI.

---

## Files Changed

| File | Change |
|------|--------|
| `config/settings.py` | Add `EMBEDDING_FIELDS`, `EMBEDDING_MODEL` |
| `services/matching/embedder.py` | **New** — `build_profile_text()`, `embed_profiles()`, `cosine_sim()`, `_get_model()` |
| `services/matching/scoring.py` | `_similarity_vector()`, `_profile_similarity()`, `get_top_matches()`, `build_similarity_matrix()` — add `embeddings` parameter |
| `requirements.txt` | Add `sentence-transformers>=3.0,<4.0` (adds PyTorch as a transitive dependency, ~1.5GB install; confirm CI environment can accommodate this) |
| `tests/test_embedder.py` | **New** |
| `tests/test_match.py` | Extend with embedding tests |

---

## What Does NOT Change

- `similarity.py` — all hand-crafted functions unchanged
- `distance.py` — unchanged; `build_combined_distance()` calls `build_similarity_matrix(profiles)` with no embeddings arg, which is still valid (embeddings computed internally by the new default-`None` parameter)
- `pipeline.py` — unchanged; calls `build_combined_distance()`, not `build_similarity_matrix()` directly
- `projector.py`, `writer.py`, `ego.py`, `scheduler.py` — unchanged
- All weights in `PROFILE_WEIGHTS` — unchanged
- Supabase schema — no migrations needed
- Frontend — no changes
