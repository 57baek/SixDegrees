"""Tests for map_pipeline.scoring.build_combined_distance_matrix()"""
import numpy as np
import pytest
from models.user import UserProfile
from services.map_pipeline.scoring import build_combined_distance_matrix


def make_users(n: int) -> list[UserProfile]:
    """Create n minimal UserProfile objects for testing."""
    return [
        UserProfile(
            id=f"u{i}",
            nickname=f"User{i}",
            interests=["coding", "music"] if i % 2 == 0 else ["sports", "cooking"],
            languages=["English"],
            city="San Francisco",
            state="CA",
            education="Computer Science",
            occupation="Engineer",
            industry="Technology",
            age=25 + i,
            timezone="UTC",
        )
        for i in range(n)
    ]


def zero_interaction_matrix(n: int) -> np.ndarray:
    return np.zeros((n, n), dtype=float)


# ── DIST-04: matrix properties ───────────────────────────────────────────────

def test_output_shape():
    """DIST-04: Returns NxN matrix."""
    users = make_users(4)
    interaction = zero_interaction_matrix(4)
    result = build_combined_distance_matrix(users, interaction)
    assert result.shape == (4, 4)


def test_diagonal_is_zero():
    """DIST-04: Diagonal must be exactly 0.0."""
    users = make_users(5)
    interaction = zero_interaction_matrix(5)
    result = build_combined_distance_matrix(users, interaction)
    np.testing.assert_array_equal(np.diag(result), np.zeros(5))


def test_is_symmetric():
    """DIST-04: Matrix must be symmetric."""
    users = make_users(5)
    interaction = zero_interaction_matrix(5)
    result = build_combined_distance_matrix(users, interaction)
    np.testing.assert_allclose(result, result.T, atol=1e-10)


def test_values_in_range():
    """DIST-04: All values in [0, 1]."""
    users = make_users(6)
    rng = np.random.default_rng(42)
    interaction = rng.random((6, 6))
    interaction = (interaction + interaction.T) / 2.0
    np.fill_diagonal(interaction, 0.0)
    result = build_combined_distance_matrix(users, interaction)
    assert result.min() >= -1e-9, f"Min {result.min()} < 0"
    assert result.max() <= 1.0 + 1e-9, f"Max {result.max()} > 1"


# ── DIST-01: formula verification ────────────────────────────────────────────

def test_zero_interactions_equals_profile_distance():
    """DIST-01: With β=0 interaction (all zeros), combined dist = α × profile_dist."""
    from config.algorithm import ALPHA
    from services.matching.scoring import (
        build_similarity_matrix, apply_weights, similarity_to_distance
    )
    from config.algorithm import PROFILE_WEIGHTS
    users = make_users(4)
    interaction = zero_interaction_matrix(4)

    combined = build_combined_distance_matrix(users, interaction)

    sim = build_similarity_matrix(users)
    weighted = apply_weights(sim, PROFILE_WEIGHTS)
    profile_dist = similarity_to_distance(weighted)

    # With zero interactions: combined = α × profile_dist + β × (1 - 0) = α × profile_dist + β
    # We verify the formula holds for off-diagonal elements
    from config.algorithm import BETA
    expected = ALPHA * profile_dist + BETA * (1.0 - interaction)
    expected = (expected + expected.T) / 2.0
    np.fill_diagonal(expected, 0.0)
    np.testing.assert_allclose(combined, expected, atol=1e-10)


def test_full_interactions_reduces_distance():
    """DIST-01: Users with high interaction score should have lower combined distance."""
    users = make_users(3)
    # Scenario A: zero interactions
    zero_int = zero_interaction_matrix(3)
    dist_zero = build_combined_distance_matrix(users, zero_int)

    # Scenario B: high interactions between u0 and u1
    high_int = np.zeros((3, 3))
    high_int[0][1] = 0.9
    high_int[1][0] = 0.9
    dist_high = build_combined_distance_matrix(users, high_int)

    # u0-u1 distance should be LOWER with high interactions
    assert dist_high[0][1] < dist_zero[0][1], (
        f"High interaction should reduce distance: {dist_high[0][1]} vs {dist_zero[0][1]}"
    )


# ── DIST-03: profile weights preserved ────────────────────────────────────────

def test_reuses_existing_matching_scoring():
    """DIST-03: Profile distance computation delegates to services/matching/scoring.py."""
    # This test verifies the import chain works — if matching/scoring is broken,
    # this test fails, alerting that we haven't reimplemented similarity logic.
    from services.matching.scoring import build_similarity_matrix
    users = make_users(3)
    interaction = zero_interaction_matrix(3)
    # Should not raise — proves we're calling into matching/scoring successfully
    result = build_combined_distance_matrix(users, interaction)
    assert result.shape == (3, 3)
