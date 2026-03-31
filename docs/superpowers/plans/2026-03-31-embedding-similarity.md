# Embedding-Based Profile Similarity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Jaccard interest score in profile matching with sentence-transformer embeddings + cosine similarity, folding `bio` into the same embedding, while keeping all other hand-crafted scores unchanged.

**Architecture:** A new `embedder.py` module handles model lifecycle (lazy load), text assembly, and batch encoding. `scoring.py` is updated to pass an `embeddings` dict through `_similarity_vector`, `_profile_similarity`, `get_top_matches`, and `build_similarity_matrix`. When `EMBEDDING_FIELDS == []`, `embed_profiles` is never called and scoring falls back to Jaccard entirely. `EMBEDDING_FIELDS` in `settings.py` controls which fields go through embeddings.

**Tech Stack:** Python, sentence-transformers (`all-MiniLM-L6-v2`), numpy, pytest, unittest.mock

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `backend/requirements.txt` | Modify | Add `sentence-transformers>=3.0,<4.0` |
| `backend/config/settings.py` | Modify | Add `EMBEDDING_FIELDS`, `EMBEDDING_MODEL` constants |
| `backend/services/matching/embedder.py` | **Create** | `build_profile_text()`, `cosine_sim()`, `_get_model()`, `embed_profiles()` |
| `backend/services/matching/scoring.py` | Modify | Add `embeddings` param to `_similarity_vector`, `_profile_similarity`, `get_top_matches`, `build_similarity_matrix` |
| `backend/tests/test_embedder.py` | **Create** | Unit + integration tests for `embedder.py` |
| `backend/tests/test_match.py` | Modify | Add autouse mock fixture + `test_embedding_fields_config`, `test_semantic_similarity` |

---

## Task 1: Add dependency and config constants

**Files:**
- Modify: `backend/requirements.txt`
- Modify: `backend/config/settings.py`

- [ ] **Step 1: Add `sentence-transformers` to requirements.txt**

Open `backend/requirements.txt` and add after the `umap-learn` line:

```
sentence-transformers>=3.0,<4.0
```

- [ ] **Step 2: Install the dependency**

```bash
cd backend && source venv/bin/activate && pip install "sentence-transformers>=3.0,<4.0"
```

Expected: installs successfully (pulls PyTorch transitively — expect ~1.5GB, takes a few minutes on first install).

- [ ] **Step 3: Add config constants to `settings.py`**

Add these two constants at the end of `backend/config/settings.py`, after `TIER2_K`:

```python
# --- Embeddings ---
# Fields whose similarity is computed via sentence-transformer embeddings.
# Replaces hand-crafted counterparts in the weighted profile score.
# Set to [] to disable embeddings and fall back to hand-crafted methods.
EMBEDDING_FIELDS: list[str] = ["interests", "bio"]

# Sentence-transformers model — downloads once on first run (~90MB)
EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
```

- [ ] **Step 4: Verify import works**

```bash
cd backend && source venv/bin/activate && python -c "from config.settings import EMBEDDING_FIELDS, EMBEDDING_MODEL; print(EMBEDDING_FIELDS, EMBEDDING_MODEL)"
```

Expected output: `['interests', 'bio'] all-MiniLM-L6-v2`

- [ ] **Step 5: Commit**

```bash
cd backend && git add requirements.txt config/settings.py && git commit -m "feat: add sentence-transformers dep and EMBEDDING_FIELDS config"
```

---

## Task 2: Write and pass tests for `build_profile_text` and `cosine_sim`

These are pure functions with no model dependency — test them first.

**Files:**
- Create: `backend/tests/test_embedder.py`
- Create: `backend/services/matching/embedder.py` (skeleton + these two functions only)

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_embedder.py`:

```python
"""Tests for services/matching/embedder.py."""

import numpy as np
import pytest
from unittest.mock import patch

from services.matching.embedder import build_profile_text, cosine_sim
from models.user import UserProfile


def _profile(**kwargs) -> UserProfile:
    """Helper: build a UserProfile with defaults for required fields."""
    defaults = {"id": "u1", "nickname": "Test"}
    return UserProfile(**{**defaults, **kwargs})


# --- build_profile_text ---

def test_build_profile_text_full():
    """interests + bio → space-joined interests, period separator, bio."""
    p = _profile(interests=["hiking", "trail running"], bio="I love the outdoors")
    result = build_profile_text(p)
    assert result == "hiking trail running. I love the outdoors"


def test_build_profile_text_interests_only():
    """bio=None → interests only, no trailing separator."""
    p = _profile(interests=["hiking", "photography"], bio=None)
    result = build_profile_text(p)
    assert result == "hiking photography"


def test_build_profile_text_bio_only():
    """EMBEDDING_FIELDS=['bio'] → bio text only, no leading separator."""
    p = _profile(interests=["hiking"], bio="I love the outdoors")
    with patch("services.matching.embedder.EMBEDDING_FIELDS", ["bio"]):
        result = build_profile_text(p)
    assert result == "I love the outdoors"


def test_build_profile_text_empty():
    """No interests, no bio → empty string, no crash."""
    p = _profile(interests=[], bio=None)
    result = build_profile_text(p)
    assert result == ""


def test_build_profile_text_empty_interests_with_bio():
    """Empty interests list + bio → bio only (no leading separator)."""
    p = _profile(interests=[], bio="I love music")
    result = build_profile_text(p)
    assert result == "I love music"


# --- cosine_sim ---

def test_cosine_sim_identical():
    """Identical non-zero vectors → 1.0."""
    v = np.array([1.0, 2.0, 3.0])
    assert cosine_sim(v, v) == pytest.approx(1.0)


def test_cosine_sim_zero_vector_a():
    """First vector is zero → 0.0, no crash."""
    a = np.zeros(3)
    b = np.array([1.0, 0.0, 0.0])
    assert cosine_sim(a, b) == 0.0


def test_cosine_sim_zero_vector_b():
    """Second vector is zero → 0.0, no crash."""
    a = np.array([1.0, 0.0, 0.0])
    b = np.zeros(3)
    assert cosine_sim(a, b) == 0.0


def test_cosine_sim_both_zero():
    """Both vectors zero → 0.0, no nan."""
    a = np.zeros(3)
    b = np.zeros(3)
    result = cosine_sim(a, b)
    assert result == 0.0
    assert not np.isnan(result)


def test_cosine_sim_result_clipped():
    """Result is clipped to [0, 1] (no negative values)."""
    a = np.array([1.0, 0.0])
    b = np.array([0.0, 1.0])
    result = cosine_sim(a, b)
    assert 0.0 <= result <= 1.0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && source venv/bin/activate && python -m pytest tests/test_embedder.py -v 2>&1 | head -30
```

Expected: `ImportError` or `ModuleNotFoundError` — `embedder.py` doesn't exist yet.

- [ ] **Step 3: Create `embedder.py` with `build_profile_text` and `cosine_sim`**

Create `backend/services/matching/embedder.py`:

```python
"""Sentence-transformer embedding for profile text fields.

Model lifecycle: lazy-loaded on first call to embed_profiles().
Not thread-safe — safe under single-worker Uvicorn deployment.
"""

import numpy as np
from sentence_transformers import SentenceTransformer

from config.settings import EMBEDDING_FIELDS, EMBEDDING_MODEL
from models.user import UserProfile

_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    """Return the shared model instance, loading it on first call."""
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBEDDING_MODEL)
    return _model


def build_profile_text(profile: UserProfile) -> str:
    """Concatenate EMBEDDING_FIELDS values into a single string for embedding.

    Rules (reads EMBEDDING_FIELDS from config at call time — patchable in tests):
      - list[str] fields: space-joined
      - str fields: used as-is
      - None or empty list: skipped (no separator emitted)
    Non-empty parts joined with ". " between them.

    Examples (EMBEDDING_FIELDS = ["interests", "bio"]):
      interests=["hiking", "trail running"], bio="I love the outdoors"
        → "hiking trail running. I love the outdoors"
      interests=["hiking"], bio=None  → "hiking"
      interests=[],         bio="..."  → "I love the outdoors"
      interests=[],         bio=None   → ""
    """
    parts: list[str] = []
    for field in EMBEDDING_FIELDS:
        value = getattr(profile, field, None)
        if value is None:
            continue
        if isinstance(value, list):
            text = " ".join(value).strip()
        else:
            text = str(value).strip()
        if text:
            parts.append(text)
    return ". ".join(parts)


def cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity between two vectors, clipped to [0, 1].

    Returns 0.0 if either vector is all-zeros (avoids division-by-zero / nan).
    """
    norm_a = float(np.linalg.norm(a))
    norm_b = float(np.linalg.norm(b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    raw = float(np.dot(a, b) / (norm_a * norm_b))
    return float(np.clip(raw, 0.0, 1.0))


def embed_profiles(profiles: list[UserProfile]) -> np.ndarray:
    """Batch-encode profiles using EMBEDDING_FIELDS text. Returns shape (N, 384).

    Profiles with empty text receive np.zeros(384) directly — the model is NOT
    called with empty strings (model output on empty tokens is undefined).
    Precondition: profile IDs in the input list must be unique.

    Note: output dim is hardcoded to 384 for all-MiniLM-L6-v2. If EMBEDDING_MODEL
    is changed to a different model, update this value accordingly.
    """
    n = len(profiles)
    texts = [build_profile_text(p) for p in profiles]

    non_empty_indices = [i for i, t in enumerate(texts) if t]
    non_empty_texts = [texts[i] for i in non_empty_indices]

    dim = 384
    result = np.zeros((n, dim), dtype=np.float32)

    if non_empty_texts:
        model = _get_model()
        encoded = model.encode(non_empty_texts, convert_to_numpy=True)
        for out_idx, src_idx in enumerate(non_empty_indices):
            result[src_idx] = encoded[out_idx]

    return result
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && source venv/bin/activate && python -m pytest tests/test_embedder.py -v -k "not embed_profiles"
```

Expected: all `test_build_profile_text_*` and `test_cosine_sim_*` tests pass.

- [ ] **Step 5: Commit**

```bash
cd backend && git add services/matching/embedder.py tests/test_embedder.py && git commit -m "feat: add embedder.py with build_profile_text and cosine_sim"
```

---

## Task 3: Write and pass `embed_profiles` integration tests

These tests call the real model — they run once at test time (model cached in memory).

**Files:**
- Modify: `backend/tests/test_embedder.py`

- [ ] **Step 1: Add integration tests — append to `backend/tests/test_embedder.py`**

```python
# --- embed_profiles (uses real model — sentence-transformers must be installed) ---

def test_embed_profiles_shape():
    """N profiles → output shape (N, 384)."""
    from services.matching.embedder import embed_profiles
    profiles = [
        _profile(id="u1", interests=["hiking"], bio="outdoor person"),
        _profile(id="u2", interests=["coding"], bio="software engineer"),
        _profile(id="u3", interests=[], bio=None),
    ]
    result = embed_profiles(profiles)
    assert result.shape == (3, 384)


def test_embed_profiles_empty_profile_is_zero():
    """Profile with no text gets a zero vector."""
    from services.matching.embedder import embed_profiles
    profiles = [_profile(id="u1", interests=[], bio=None)]
    result = embed_profiles(profiles)
    assert np.all(result[0] == 0.0)


def test_embed_profiles_identical_profiles_cosine_one():
    """Same profile text twice → cosine sim = 1.0."""
    from services.matching.embedder import embed_profiles
    profiles = [
        _profile(id="u1", interests=["hiking", "camping"], bio="I love nature"),
        _profile(id="u2", interests=["hiking", "camping"], bio="I love nature"),
    ]
    result = embed_profiles(profiles)
    sim = cosine_sim(result[0], result[1])
    assert sim == pytest.approx(1.0, abs=1e-5)
```

- [ ] **Step 2: Run the integration tests**

```bash
cd backend && source venv/bin/activate && python -m pytest tests/test_embedder.py -v
```

Expected: all tests pass. The first run may download the model (~90MB) — subsequent runs are instant.

- [ ] **Step 3: Commit**

```bash
cd backend && git add tests/test_embedder.py && git commit -m "test: add embed_profiles integration tests"
```

---

## Task 4: Update `scoring.py` and write new scoring tests

This is the core wiring change. Follow TDD: write failing tests first, then implement.

**Files:**
- Modify: `backend/tests/test_match.py`
- Modify: `backend/services/matching/scoring.py`

- [ ] **Step 1: Add imports and autouse fixture to `backend/tests/test_match.py`**

Add these imports at the **top** of `backend/tests/test_match.py`, after the existing import block (lines 1–7):

```python
import numpy as np
from models.user import UserProfile
from services.matching.scoring import get_top_matches
```

Then add this autouse fixture immediately after the imports, before the existing `_FULL_PROFILE_ROWS` definition. This fixture automatically mocks `embed_profiles` for ALL tests in this file — the mock returns a zero matrix sized to match however many profiles the call receives, so shape never mismatches:

```python
@pytest.fixture(autouse=True)
def mock_embed_profiles(monkeypatch):
    """Patch embed_profiles in scoring.py for all tests in this file.

    Returns np.zeros((N, 384)) where N matches the number of profiles passed.
    This prevents the real sentence-transformer model from loading during tests.
    """
    def _zero_embed(profiles):
        return np.zeros((len(profiles), 384), dtype=np.float32)

    monkeypatch.setattr("services.matching.scoring.embed_profiles", _zero_embed)
```

- [ ] **Step 2: Add the two new test functions — append to the bottom of `backend/tests/test_match.py`**

```python
# --- Embedding-based scoring unit tests ---
# Test scoring.py directly, using mock embeddings to avoid model load.

def _user(uid: str, interests: list[str], bio: str | None = None) -> UserProfile:
    return UserProfile(id=uid, nickname=uid, interests=interests, bio=bio)


def test_embedding_fields_config_fallback_to_jaccard(monkeypatch):
    """When EMBEDDING_FIELDS=[], get_top_matches uses Jaccard and never calls embed_profiles."""
    from unittest.mock import MagicMock
    monkeypatch.setattr("services.matching.scoring.EMBEDDING_FIELDS", [])

    mock_embed = MagicMock()
    monkeypatch.setattr("services.matching.scoring.embed_profiles", mock_embed)

    current = _user("me", interests=["coding", "music"])
    other = _user("u1", interests=["coding", "music"])
    results = get_top_matches(current, [other], top_n=1)

    mock_embed.assert_not_called()
    assert len(results) == 1
    # Jaccard of identical interests = 1.0 * 0.4 weight = 0.4 (at minimum)
    assert results[0]["similarity_score"] > 0.0


def test_semantic_similarity_scores_higher_than_jaccard(monkeypatch):
    """Embedding cosine sim for related interests beats Jaccard.

    'hiking' and 'trail running' share zero tokens → Jaccard = 0.0.
    We inject vectors with cosine_sim ≈ 0.9 to simulate the model
    correctly identifying them as semantically related.
    """
    current = _user("me", interests=["hiking"])
    other = _user("u1", interests=["trail running"])

    # Baseline: Jaccard (EMBEDDING_FIELDS disabled)
    monkeypatch.setattr("services.matching.scoring.EMBEDDING_FIELDS", [])
    jaccard_score = get_top_matches(current, [other], top_n=1)[0]["similarity_score"]

    # Embedding: inject vectors where cosine_sim("me", "u1") ≈ 0.9
    # get_top_matches calls embed_profiles(all_users + [current_user])
    # = embed_profiles([other, current]) — other is index 0, current is index 1
    v_other = np.zeros(384, dtype=np.float32)
    v_other[0] = 0.9
    v_other[1] = float(np.sqrt(1.0 - 0.9**2))  # unit vector, cos with v_current ≈ 0.9

    v_current = np.zeros(384, dtype=np.float32)
    v_current[0] = 1.0  # unit vector along dim 0

    def _embed_with_vectors(profiles):
        result = np.zeros((len(profiles), 384), dtype=np.float32)
        for i, p in enumerate(profiles):
            if p.id == "u1":
                result[i] = v_other
            elif p.id == "me":
                result[i] = v_current
        return result

    monkeypatch.setattr("services.matching.scoring.EMBEDDING_FIELDS", ["interests", "bio"])
    monkeypatch.setattr("services.matching.scoring.embed_profiles", _embed_with_vectors)

    embedding_score = get_top_matches(current, [other], top_n=1)[0]["similarity_score"]

    assert embedding_score > jaccard_score, (
        f"Expected embedding score ({embedding_score}) > jaccard score ({jaccard_score})"
    )
```

- [ ] **Step 3: Run new tests to verify they fail**

```bash
cd backend && source venv/bin/activate && python -m pytest tests/test_match.py::test_embedding_fields_config_fallback_to_jaccard tests/test_match.py::test_semantic_similarity_scores_higher_than_jaccard -v
```

Expected: both fail — `get_top_matches` doesn't have embedding logic yet.

- [ ] **Step 4: Replace `backend/services/matching/scoring.py` with the updated version**

Replace the entire file contents with:

```python
import numpy as np
from models.user import UserProfile
from config.settings import PROFILE_WEIGHTS, EMBEDDING_FIELDS
from services.matching.embedder import embed_profiles, cosine_sim
from services.matching.similarity import (
    jaccard,
    tiered_location,
    tiered_categorical,
    inverse_distance_age,
    FIELD_OF_STUDY_CATEGORIES,
    INDUSTRY_CATEGORIES,
)

# Tunable weights. Must sum to 1.0.
DEFAULT_WEIGHTS: dict[str, float] = {
    "interests":  0.40,
    "location":   0.20,
    "languages":  0.15,
    "education":  0.10,
    "industry":   0.10,
    "age":        0.05,
}

FEATURE_COLS = list(DEFAULT_WEIGHTS.keys())


def _build_embeddings(profiles: list[UserProfile]) -> dict[str, np.ndarray]:
    """Embed profiles and return a dict keyed by user ID.

    Only called when EMBEDDING_FIELDS is non-empty.
    """
    raw = embed_profiles(profiles)
    return {profiles[i].id: raw[i] for i in range(len(profiles))}


def _text_score(u1: UserProfile, u2: UserProfile, embeddings: dict[str, np.ndarray]) -> float:
    """Return the interests-slot score: cosine sim (embedding) or Jaccard fallback.

    Checks EMBEDDING_FIELDS at call time so tests can patch it.
    """
    if "interests" in EMBEDDING_FIELDS or "bio" in EMBEDDING_FIELDS:
        return cosine_sim(embeddings[u1.id], embeddings[u2.id])
    return jaccard(u1.interests, u2.interests, stem=True)


def _similarity_vector(
    u1: UserProfile,
    u2: UserProfile,
    embeddings: dict[str, np.ndarray],
) -> list[float]:
    """Compute raw [0,1] similarity score per field for a user pair."""
    return [
        _text_score(u1, u2, embeddings),
        tiered_location(u1.city, u1.state, u2.city, u2.state),
        jaccard(u1.languages, u2.languages),
        tiered_categorical(u1.education, u2.education, FIELD_OF_STUDY_CATEGORIES),
        tiered_categorical(u1.industry, u2.industry, INDUSTRY_CATEGORIES),
        inverse_distance_age(u1.age, u2.age),
    ]


def _profile_similarity(
    u1: UserProfile,
    u2: UserProfile,
    embeddings: dict[str, np.ndarray],
) -> float:
    """Weighted similarity score in [0, 1] between two users."""
    scores = _similarity_vector(u1, u2, embeddings)
    weights = [
        PROFILE_WEIGHTS["interests"],
        PROFILE_WEIGHTS["location"],
        PROFILE_WEIGHTS["languages"],
        PROFILE_WEIGHTS["education"],
        PROFILE_WEIGHTS["industry"],
        PROFILE_WEIGHTS["age"],
    ]
    return sum(s * w for s, w in zip(scores, weights))


def get_top_matches(
    current_user: UserProfile,
    all_users: list[UserProfile],
    top_n: int = 10,
) -> list[dict]:
    """Return top_n most similar users sorted by descending similarity score.

    all_users must NOT include current_user.
    Returns list of {"user": UserProfile, "similarity_score": float}.

    When EMBEDDING_FIELDS is empty, embed_profiles is never called and scoring
    falls back to Jaccard for interests.
    """
    all_profiles = all_users + [current_user]
    if EMBEDDING_FIELDS:
        embeddings = _build_embeddings(all_profiles)
    else:
        # No embedding fields configured — use zero vectors (Jaccard will be used instead)
        embeddings = {p.id: np.zeros(384, dtype=np.float32) for p in all_profiles}

    scored = [
        {"user": u, "similarity_score": round(_profile_similarity(current_user, u, embeddings), 4)}
        for u in all_users
    ]
    scored.sort(key=lambda x: x["similarity_score"], reverse=True)
    return scored[:top_n]


def build_similarity_matrix(
    users: list[UserProfile],
    embeddings: dict[str, np.ndarray] | None = None,
) -> np.ndarray:
    """Build an (N x N x F) matrix of per-field similarity scores.

    Returns shape (N, N, F) where F = number of feature dimensions.
    sim[i][j] is a vector of per-field similarity scores between users[i] and users[j].

    If embeddings is None, computes them internally.
    When EMBEDDING_FIELDS is empty, uses zero vectors (Jaccard fallback via _text_score).
    """
    if embeddings is None:
        if EMBEDDING_FIELDS:
            embeddings = _build_embeddings(users)
        else:
            embeddings = {p.id: np.zeros(384, dtype=np.float32) for p in users}

    n = len(users)
    f = len(FEATURE_COLS)
    matrix = np.zeros((n, n, f))
    for i in range(n):
        for j in range(i + 1, n):
            vec = _similarity_vector(users[i], users[j], embeddings)
            matrix[i][j] = vec
            matrix[j][i] = vec  # symmetric
    return matrix


def apply_weights(
    sim_matrix: np.ndarray,
    weights: dict[str, float] = DEFAULT_WEIGHTS,
) -> np.ndarray:
    """Dot-multiply each feature dimension by its weight.

    Returns a (N, N) matrix of weighted similarity scores in [0, 1].
    Higher score = more similar.
    """
    weight_vec = np.array([weights[col] for col in FEATURE_COLS])
    return np.dot(sim_matrix, weight_vec)


def similarity_to_distance(weighted_scores: np.ndarray) -> np.ndarray:
    """Convert similarity scores to distances: distance = 1 - similarity.

    Returns a (N, N) distance matrix where 0 = identical, 1 = maximally different.
    """
    dist = 1.0 - weighted_scores
    np.fill_diagonal(dist, 0.0)
    return dist
```

- [ ] **Step 5: Run the two new tests**

```bash
cd backend && source venv/bin/activate && python -m pytest tests/test_match.py::test_embedding_fields_config_fallback_to_jaccard tests/test_match.py::test_semantic_similarity_scores_higher_than_jaccard -v
```

Expected: both pass.

- [ ] **Step 6: Run the full test suite**

```bash
cd backend && source venv/bin/activate && python -m pytest -q
```

Expected: all tests pass. The autouse `mock_embed_profiles` fixture prevents the real model from loading for any test in `test_match.py`. Other test files (e.g. `tests/map/test_distance.py`) that call `build_similarity_matrix` or `build_combined_distance` may also need their own `embed_profiles` mock — if they fail, add the same monkeypatch to those test files' fixtures.

- [ ] **Step 7: Commit**

```bash
cd backend && git add services/matching/scoring.py tests/test_match.py && git commit -m "feat: wire embedding cosine sim into profile scoring"
```

---

## Task 5: Final verification

- [ ] **Step 1: Run the complete test suite**

```bash
cd backend && source venv/bin/activate && python -m pytest -q
```

Expected: all tests pass with no import warnings.

- [ ] **Step 2: Verify all modules import cleanly**

```bash
cd backend && source venv/bin/activate && python -c "
from services.matching.embedder import build_profile_text, cosine_sim, embed_profiles
from services.matching.scoring import get_top_matches, build_similarity_matrix
from config.settings import EMBEDDING_FIELDS, EMBEDDING_MODEL
print('All imports OK')
print('EMBEDDING_FIELDS:', EMBEDDING_FIELDS)
print('EMBEDDING_MODEL:', EMBEDDING_MODEL)
"
```

Expected output:
```
All imports OK
EMBEDDING_FIELDS: ['interests', 'bio']
EMBEDDING_MODEL: all-MiniLM-L6-v2
```

Note: this does NOT trigger the model download — the model loads lazily on first `embed_profiles()` call.

- [ ] **Step 3: Final commit if anything was touched**

```bash
cd backend && git status
```

Only commit if there are uncommitted changes.
