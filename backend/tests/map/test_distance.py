"""Tests for services/map/distance.py — build_combined_distance."""

import numpy as np
import pytest

from models.user import UserProfile
from services.map.contracts import PipelineInput
from services.map.distance import build_combined_distance


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_profile(uid: str, **kwargs) -> UserProfile:
    """Create a minimal valid UserProfile. Keyword args override defaults."""
    defaults = dict(
        id=uid,
        nickname=f"user_{uid}",
        age=25,
        city="Springfield",
        state="IL",
        education="computer science",
        industry="software",
        interests=["hiking", "cooking"],
        languages=["english"],
    )
    defaults.update(kwargs)
    return UserProfile(**defaults)


def make_interaction(uid_a: str, uid_b: str, like_count: int = 0,
                     comment_count: int = 0, dm_count: int = 0) -> dict:
    """Return an interaction row with canonical ordering (uid_a < uid_b).

    Column names match the DB schema: likes_count, comments_count, dm_count.
    """
    a, b = min(uid_a, uid_b), max(uid_a, uid_b)
    return {
        "user_id_a": a,
        "user_id_b": b,
        "likes_count": like_count,
        "comments_count": comment_count,
        "dm_count": dm_count,
    }


# ---------------------------------------------------------------------------
# Test 1: Output shape
# ---------------------------------------------------------------------------

def test_output_shape():
    profiles = [make_profile(str(i)) for i in range(5)]
    data = PipelineInput(profiles=profiles, interactions=[])
    m = build_combined_distance(data)
    assert m.shape == (5, 5)


# ---------------------------------------------------------------------------
# Test 2: Symmetry
# ---------------------------------------------------------------------------

def test_matrix_is_symmetric():
    profiles = [make_profile(str(i)) for i in range(4)]
    interactions = [
        make_interaction("0", "1", like_count=3, comment_count=1),
        make_interaction("2", "3", dm_count=5),
    ]
    data = PipelineInput(profiles=profiles, interactions=interactions)
    m = build_combined_distance(data)
    assert np.allclose(m, m.T), "Distance matrix must be symmetric"


# ---------------------------------------------------------------------------
# Test 3: Diagonal is zero
# ---------------------------------------------------------------------------

def test_diagonal_is_zero():
    profiles = [make_profile(str(i)) for i in range(4)]
    data = PipelineInput(profiles=profiles, interactions=[])
    m = build_combined_distance(data)
    assert np.allclose(np.diag(m), 0.0), "Diagonal must be all zeros"


# ---------------------------------------------------------------------------
# Test 4: Values in [0, 1]
# ---------------------------------------------------------------------------

def test_values_in_unit_range():
    profiles = [make_profile(str(i)) for i in range(5)]
    interactions = [make_interaction("0", "2", like_count=10, comment_count=5, dm_count=3)]
    data = PipelineInput(profiles=profiles, interactions=interactions)
    m = build_combined_distance(data)
    assert m.min() >= 0.0, f"Min value {m.min()} is below 0"
    assert m.max() <= 1.0, f"Max value {m.max()} is above 1"


# ---------------------------------------------------------------------------
# Test 5: High interaction drives distance down
# ---------------------------------------------------------------------------

def test_interaction_drives_distance_down():
    """
    Three identical profiles A, B, C (same profile similarity).
    A & B have high interactions; A & C have none.
    Expected: m[A][B] < m[A][C].
    """
    # Make all profiles identical so profile_dist is the same for every pair
    common = dict(
        age=30,
        city="Austin",
        state="TX",
        education="computer science",
        industry="software",
        interests=["hiking", "cooking", "reading"],
        languages=["english", "spanish"],
    )
    # Use IDs that sort correctly: "a" < "b" < "c" lexicographically
    uid_a, uid_b, uid_c = "a", "b", "c"
    profiles = [
        make_profile(uid_a, **common),
        make_profile(uid_b, **common),
        make_profile(uid_c, **common),
    ]

    # A & B interact heavily; A & C have no interaction
    interactions = [
        make_interaction(uid_a, uid_b, like_count=50, comment_count=30, dm_count=20),
    ]

    data = PipelineInput(profiles=profiles, interactions=interactions)
    m = build_combined_distance(data)

    idx = {uid_a: 0, uid_b: 1, uid_c: 2}
    dist_ab = m[idx[uid_a]][idx[uid_b]]
    dist_ac = m[idx[uid_a]][idx[uid_c]]

    assert dist_ab < dist_ac, (
        f"Expected dist(A,B)={dist_ab:.4f} < dist(A,C)={dist_ac:.4f} "
        "because A & B have heavy interactions"
    )


# ---------------------------------------------------------------------------
# Test 6: Empty interactions — no crash
# ---------------------------------------------------------------------------

def test_empty_interactions_no_crash():
    profiles = [make_profile(str(i)) for i in range(3)]
    data = PipelineInput(profiles=profiles, interactions=[])
    m = build_combined_distance(data)  # must not raise
    assert m.shape == (3, 3)
    assert np.allclose(np.diag(m), 0.0)
    assert np.allclose(m, m.T)
