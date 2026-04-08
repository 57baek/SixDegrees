"""Tests verifying None-safety of similarity functions and _profile_similarity."""

import sys
import os

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.matching.similarity import (
    tiered_location,
    inverse_distance_age,
    tiered_categorical,
    FIELD_OF_STUDY_CATEGORIES,
)
from services.matching.scoring import _profile_similarity
from models.user import UserProfile


def test_tiered_location_none_args():
    assert tiered_location(None, None, "NYC", "NY") == 0.0


def test_tiered_location_partial_none():
    assert tiered_location("SF", None, "SF", "CA") == 0.0
    assert tiered_location(None, "CA", "SF", "CA") == 0.0
    assert tiered_location("SF", "CA", None, "CA") == 0.0
    assert tiered_location("SF", "CA", "SF", None) == 0.0


def test_inverse_distance_age_none_first():
    assert inverse_distance_age(None, 28) == 0.0


def test_inverse_distance_age_none_second():
    assert inverse_distance_age(30, None) == 0.0


def test_inverse_distance_age_both_none():
    assert inverse_distance_age(None, None) == 0.0


def test_tiered_categorical_none_first():
    assert tiered_categorical(None, "bachelor", FIELD_OF_STUDY_CATEGORIES) == 0.0


def test_tiered_categorical_none_second():
    assert tiered_categorical("computer science", None, FIELD_OF_STUDY_CATEGORIES) == 0.0


def test_tiered_categorical_both_none():
    assert tiered_categorical(None, None, FIELD_OF_STUDY_CATEGORIES) == 0.0


def test_profile_similarity_all_none_optionals():
    """UserProfile with all None optional fields must not crash _profile_similarity."""
    u1 = UserProfile(id="u1", nickname="Alice")
    u2 = UserProfile(id="u2", nickname="Bob")
    embeddings = {
        "u1": np.zeros(384, dtype=np.float32),
        "u2": np.zeros(384, dtype=np.float32),
    }
    score = _profile_similarity(u1, u2, embeddings)
    assert isinstance(score, float)
    assert 0.0 <= score <= 1.0
