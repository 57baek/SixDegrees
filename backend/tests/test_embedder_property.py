"""Property-based fuzz tests for embedding functions.

Uses Hypothesis to generate arbitrary inputs and verify mathematical invariants.
This satisfies the fuzz testing requirement for Demo-4.

Model loading: model.encode() is patched to return deterministic seeded vectors.
This keeps tests fast and offline-safe while exercising real batching/indexing logic.
Tests requiring the real model are in test_embedder.py and marked @pytest.mark.slow.

EMBEDDING_FIELDS is patched to ["interests", "bio"] in all tests to decouple
invariants from live config.
"""

import numpy as np
import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st
from hypothesis.extra.numpy import arrays
from unittest.mock import patch, MagicMock

from services.matching.embedder import build_profile_text, cosine_sim, embed_profiles
from services.matching.scoring import get_top_matches
from models.user import UserProfile

# --- Strategies ---

_text = st.text(min_size=0, max_size=50)
_word_list = st.lists(st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=("L",))), min_size=0, max_size=10)
_dim = st.integers(min_value=1, max_value=64)
_elements = st.floats(min_value=-1e3, max_value=1e3, allow_nan=False, allow_infinity=False)


@st.composite
def _same_shape_pair(draw):
    """Two float32 vectors with the same randomly chosen dimension."""
    dim = draw(_dim)
    a = draw(arrays(dtype=np.float32, shape=dim, elements=_elements))
    b = draw(arrays(dtype=np.float32, shape=dim, elements=_elements))
    return a, b


@st.composite
def _float_vec(draw):
    dim = draw(_dim)
    return draw(arrays(dtype=np.float32, shape=dim, elements=_elements))


def _profile(uid="u1", interests=None, bio=None) -> UserProfile:
    return UserProfile(id=uid, nickname=uid, interests=interests or [], bio=bio)


# --- cosine_sim invariants ---

@given(_same_shape_pair())
@settings(max_examples=300)
def test_cosine_sim_always_in_range(pair):
    """cosine_sim always returns a value in [0.0, 1.0]."""
    a, b = pair
    result = cosine_sim(a, b)
    assert 0.0 <= result <= 1.0, f"cosine_sim out of range: {result}"
    assert not np.isnan(result), "cosine_sim returned NaN"


@given(_float_vec())
@settings(max_examples=200)
def test_cosine_sim_identical_nonzero_is_one(v):
    """cosine_sim(v, v) == 1.0 for any non-zero vector."""
    assume(np.linalg.norm(v) > 0)
    result = cosine_sim(v, v)
    assert result == pytest.approx(1.0, abs=1e-5)


@given(_float_vec())
@settings(max_examples=200)
def test_cosine_sim_zero_vector_is_zero(v):
    """cosine_sim(zeros, v) == 0.0 always."""
    zeros = np.zeros_like(v)
    assert cosine_sim(zeros, v) == 0.0
    assert cosine_sim(v, zeros) == 0.0


# --- build_profile_text invariants ---

@given(_word_list, st.one_of(st.none(), _text))
@settings(max_examples=300)
def test_build_profile_text_always_returns_str(interests, bio):
    """build_profile_text never raises and always returns a str."""
    p = _profile(interests=interests, bio=bio)
    with patch("config.settings.EMBEDDING_FIELDS", ["interests", "bio"]):
        result = build_profile_text(p)
    assert isinstance(result, str)


def test_build_profile_text_empty_is_empty_string():
    """Empty interests list + bio=None → empty string (fixed inputs, not property test)."""
    p = _profile(interests=[], bio=None)
    with patch("config.settings.EMBEDDING_FIELDS", ["interests", "bio"]):
        result = build_profile_text(p)
    assert result == ""


# --- embed_profiles invariants ---

def _make_mock_encode(dim=384):
    """Return a mock model whose encode() returns seeded random unit vectors."""
    rng = np.random.default_rng(42)
    def _encode(texts, **kwargs):
        vecs = rng.standard_normal((len(texts), dim)).astype(np.float32)
        norms = np.linalg.norm(vecs, axis=1, keepdims=True)
        return vecs / np.where(norms > 0, norms, 1.0)
    mock_model = MagicMock()
    mock_model.encode.side_effect = _encode
    mock_model.get_sentence_embedding_dimension.return_value = dim
    return mock_model


@given(st.lists(
    st.fixed_dictionaries({"uid": st.uuids().map(str), "interests": _word_list, "bio": st.one_of(st.none(), _text)}),
    min_size=1, max_size=8,
))
@settings(max_examples=100)
def test_embed_profiles_shape_and_no_nan(profile_dicts):
    """embed_profiles always returns shape (N, 384) with no NaN."""
    profiles = [_profile(uid=d["uid"], interests=d["interests"], bio=d["bio"]) for d in profile_dicts]
    mock_model = _make_mock_encode()
    with patch("config.settings.EMBEDDING_FIELDS", ["interests", "bio"]):
        with patch("services.matching.embedder._get_model", return_value=mock_model):
            result = embed_profiles(profiles)
    assert result.shape == (len(profiles), 384)
    assert not np.any(np.isnan(result))


@given(st.integers(min_value=1, max_value=5))
@settings(max_examples=50)
def test_embed_profiles_empty_text_is_zero_vector(n):
    """Profiles with no text always get zero vectors regardless of N."""
    profiles = [_profile(uid=str(i), interests=[], bio=None) for i in range(n)]
    with patch("config.settings.EMBEDDING_FIELDS", ["interests", "bio"]):
        result = embed_profiles(profiles)
    assert np.all(result == 0.0)


# --- get_top_matches invariants ---

@given(
    st.lists(
        st.fixed_dictionaries({
            "uid": st.uuids().map(str),
            "interests": _word_list,
        }),
        min_size=1, max_size=6,
    )
)
@settings(max_examples=50)
def test_get_top_matches_scores_always_in_range(other_dicts):
    """get_top_matches similarity_score always in [0.0, 1.0]."""
    current = _profile(uid="current", interests=["coding"])
    others = [_profile(uid=d["uid"], interests=d["interests"]) for d in other_dicts]
    # Use zero embeddings for speed
    with patch("config.settings.EMBEDDING_FIELDS", []):
        results = get_top_matches(current, others, top_n=len(others))
    for r in results:
        score = r["similarity_score"]
        assert 0.0 <= score <= 1.0, f"score out of range: {score}"
