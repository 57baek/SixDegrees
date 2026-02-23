"""Tests for interaction.compute_interaction_scores()"""
import numpy as np
import pytest
from services.map_pipeline.interaction import compute_interaction_scores


# ── helpers ────────────────────────────────────────────────────────────────

def canonical_pair(a: str, b: str) -> tuple[str, str]:
    """Return canonical pair key (a < b lexicographically)."""
    return (a, b) if a < b else (b, a)


# ── INT-04: missing pairs default to 0.0 ───────────────────────────────────

def test_no_interactions_produces_zero_matrix():
    """INT-04: Empty raw_counts → all interaction scores are 0.0."""
    user_ids = ["u1", "u2", "u3"]
    matrix = compute_interaction_scores(user_ids, {})
    assert matrix.shape == (3, 3)
    np.testing.assert_array_equal(matrix, np.zeros((3, 3)))


def test_missing_pair_produces_zero():
    """INT-04: Pair not in raw_counts → 0.0 in output matrix."""
    user_ids = ["u1", "u2", "u3"]
    # Only u1-u2 has interactions; u1-u3 and u2-u3 have none
    raw_counts = {
        canonical_pair("u1", "u2"): {"likes": 5, "comments": 3, "dms": 1},
    }
    matrix = compute_interaction_scores(user_ids, raw_counts)
    i0, i1, i2 = 0, 1, 2
    # u1-u3 and u2-u3 should be 0.0
    assert matrix[i0][i2] == 0.0
    assert matrix[i1][i2] == 0.0


# ── INT-01: dict-driven weights ─────────────────────────────────────────────

def test_uses_interaction_weights_from_config():
    """INT-01: INTERACTION_WEIGHTS dict drives computation — importing it proves integration."""
    from config.algorithm import INTERACTION_WEIGHTS
    # Verify all keys in INTERACTION_WEIGHTS appear in a basic computation
    user_ids = ["u1", "u2"]
    raw_counts = {
        canonical_pair("u1", "u2"): {k: 10 for k in INTERACTION_WEIGHTS.keys()}
    }
    matrix = compute_interaction_scores(user_ids, raw_counts)
    assert matrix.shape == (2, 2)
    # Score must be > 0 since all interaction types have nonzero counts
    assert matrix[0][1] > 0.0


# ── INT-02: 95th-percentile normalization ───────────────────────────────────

def test_superuser_clipping():
    """INT-02: One user with extreme counts does not collapse all others to ~0."""
    # 8 pairs: 7 normal (count=5) + 1 superuser (count=1000)
    ids = [f"u{i}" for i in range(4)]
    raw: dict = {}
    # Normal pairs
    for a in range(4):
        for b in range(a + 1, 4):
            if a == 0 and b == 1:
                raw[canonical_pair(ids[a], ids[b])] = {"likes": 1000, "comments": 0, "dms": 0}
            else:
                raw[canonical_pair(ids[a], ids[b])] = {"likes": 5, "comments": 0, "dms": 0}
    matrix = compute_interaction_scores(ids, raw)
    # After 95th-pct clipping, normal pairs should have a meaningful non-zero score
    # (they would be ~0 without clipping when max=1000)
    normal_scores = [
        matrix[1][2], matrix[1][3], matrix[2][3]
    ]
    assert any(s > 0.01 for s in normal_scores), (
        f"Normal interaction scores collapsed to near-zero: {normal_scores}. "
        "95th-pct clipping not working."
    )


# ── INT-03: weighted sum in [0, 1] ──────────────────────────────────────────

def test_all_scores_in_range():
    """INT-03: All output values are in [0, 1]."""
    import random
    random.seed(42)
    ids = [f"u{i}" for i in range(5)]
    raw = {}
    for a in range(5):
        for b in range(a + 1, 5):
            raw[canonical_pair(ids[a], ids[b])] = {
                "likes":    random.randint(0, 50),
                "comments": random.randint(0, 30),
                "dms":      random.randint(0, 10),
            }
    matrix = compute_interaction_scores(ids, raw)
    assert matrix.min() >= 0.0, f"Min value {matrix.min()} < 0"
    assert matrix.max() <= 1.0 + 1e-9, f"Max value {matrix.max()} > 1"


def test_score_between_zero_and_one_for_high_counts():
    """INT-03: Pair with max interactions scores higher than pair with zero interactions."""
    ids = ["u1", "u2", "u3"]
    raw = {
        canonical_pair("u1", "u2"): {"likes": 100, "comments": 100, "dms": 100},
        canonical_pair("u1", "u3"): {"likes": 0, "comments": 0, "dms": 0},
    }
    matrix = compute_interaction_scores(ids, raw)
    # With two pairs (max=100, min=0), u1-u2 normalizes to 1.0 and u1-u3 to 0.0
    assert abs(matrix[0][1] - 1.0) < 1e-6, f"Expected ~1.0 for high-count pair, got {matrix[0][1]}"
    assert matrix[0][2] == 0.0, f"Expected 0.0 for zero-count pair, got {matrix[0][2]}"


# ── symmetry and diagonal ────────────────────────────────────────────────────

def test_matrix_is_symmetric():
    """Output matrix must be symmetric."""
    ids = ["u1", "u2", "u3"]
    raw = {
        canonical_pair("u1", "u2"): {"likes": 3, "comments": 1, "dms": 0},
        canonical_pair("u2", "u3"): {"likes": 0, "comments": 2, "dms": 5},
    }
    matrix = compute_interaction_scores(ids, raw)
    np.testing.assert_allclose(matrix, matrix.T, atol=1e-10)


def test_diagonal_is_zero():
    """No self-interaction — diagonal must be zeros."""
    ids = ["u1", "u2"]
    raw = {canonical_pair("u1", "u2"): {"likes": 5, "comments": 0, "dms": 0}}
    matrix = compute_interaction_scores(ids, raw)
    np.testing.assert_array_equal(np.diag(matrix), [0.0, 0.0])
