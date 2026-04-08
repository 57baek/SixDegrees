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
    with patch("config.settings.EMBEDDING_FIELDS", ["bio"]):
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
    """Anti-correlated vectors → clipped to 0.0, not a negative value."""
    a = np.array([1.0, 0.0])
    b = np.array([-1.0, 0.0])   # raw cosine = -1.0 → must clip to 0.0
    result = cosine_sim(a, b)
    assert result == 0.0


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
