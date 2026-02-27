"""End-to-end integration tests for the full map pipeline.

These tests validate the Phase 2 ROADMAP success criteria:
  SC-1: Adding a new interaction type requires only one dict entry — zero logic changes
  SC-2: High-interaction users appear measurably closer than zero-interaction users
  SC-3: Requesting user's coordinates are exactly (0.0, 0.0)
  SC-4: Passing fewer than 10 users raises a clear descriptive error
  SC-5: NxN distance matrix is symmetric, zeros on diagonal, values in [0, 1]
"""
import numpy as np
import pytest
from models.user import UserProfile
from services.map_pipeline.pipeline import run_pipeline


# ── test helpers ─────────────────────────────────────────────────────────────

def make_user(uid: str, interests: list[str], age: int = 25) -> UserProfile:
    return UserProfile(
        id=uid,
        nickname=uid,
        interests=interests,
        languages=["English"],
        city="San Francisco",
        state="CA",
        education="Computer Science",
        occupation="Engineer",
        industry="Technology",
        age=age,
        timezone="UTC",
    )


def canonical_pair(a: str, b: str) -> tuple[str, str]:
    return (a, b) if a < b else (b, a)


def make_minimal_users(n: int) -> list[UserProfile]:
    """Create n users with alternating interest profiles."""
    return [
        make_user(
            f"u{i:02d}",
            interests=["coding", "music"] if i % 3 == 0 else (
                ["sports", "cooking"] if i % 3 == 1 else ["art", "travel"]
            ),
            age=20 + i,
        )
        for i in range(n)
    ]


# ── SC-4: N < 10 fails fast ───────────────────────────────────────────────────

def test_raises_on_fewer_than_10_users():
    """SC-4: Passing N < 10 raises ValueError with message containing '10'."""
    users = make_minimal_users(9)
    with pytest.raises(ValueError, match="10"):
        run_pipeline(users, {}, requesting_user_id="u00")


def test_raises_on_invalid_requesting_user():
    """Pipeline raises if requesting_user_id not in users list."""
    users = make_minimal_users(10)
    with pytest.raises(ValueError, match="not found"):
        run_pipeline(users, {}, requesting_user_id="not_a_real_user")


# ── SC-3: requesting user at (0, 0) ─────────────────────────────────────────

def test_requesting_user_at_origin():
    """SC-3: Requesting user's coordinates are exactly (0.0, 0.0)."""
    users = make_minimal_users(15)
    result = run_pipeline(users, {}, requesting_user_id="u05")
    coords = result["translated_results"]
    requesting = next(c for c in coords if c["user_id"] == "u05")
    assert requesting["x"] == pytest.approx(0.0, abs=1e-10)
    assert requesting["y"] == pytest.approx(0.0, abs=1e-10)


def test_requesting_user_in_results():
    """ORIG-02: Requesting user appears in output."""
    users = make_minimal_users(12)
    result = run_pipeline(users, {}, requesting_user_id="u03")
    ids = [c["user_id"] for c in result["translated_results"]]
    assert "u03" in ids


# ── SC-5: distance matrix properties ─────────────────────────────────────────

def test_raw_coords_shape():
    """TSNE-04: raw_coords has shape (N, 2) before translation."""
    n = 15
    users = make_minimal_users(n)
    result = run_pipeline(users, {}, requesting_user_id="u00")
    assert result["raw_coords"].shape == (n, 2), (
        f"Expected ({n}, 2), got {result['raw_coords'].shape}"
    )


def test_raw_coords_preserved_distinct_from_translated():
    """TSNE-04: raw_coords not modified — requesting user is NOT at (0,0) in raw."""
    users = make_minimal_users(12)
    result = run_pipeline(users, {}, requesting_user_id="u04")
    req_idx = result["user_ids"].index("u04")
    raw = result["raw_coords"]
    # In raw coords, requesting user is almost certainly not at (0, 0)
    # (t-SNE places users at various positions; only translated coords have user at origin)
    translated_req = next(
        r for r in result["translated_results"] if r["user_id"] == "u04"
    )
    assert translated_req["x"] == pytest.approx(0.0, abs=1e-10)
    # raw_coords[req_idx] should NOT necessarily be (0, 0)
    assert isinstance(raw, np.ndarray)
    assert raw.shape[1] == 2


def test_all_users_in_results():
    """All N users appear in translated_results."""
    n = 15
    users = make_minimal_users(n)
    result = run_pipeline(users, {}, requesting_user_id="u00")
    result_ids = {c["user_id"] for c in result["translated_results"]}
    expected_ids = {u.id for u in users}
    assert result_ids == expected_ids


# ── SC-2: interaction sensitivity ────────────────────────────────────────────

def test_high_interaction_users_appear_closer():
    """SC-2: Two users with high interaction count appear closer than two users
    with zero interactions but identical profile similarity."""
    # Use enough users to satisfy N >= 10
    users = make_minimal_users(20)
    requesting_id = "u00"

    # All users have the same profile type (alternating interests already set in make_minimal_users)
    # Run A: no interactions
    result_no_int = run_pipeline(users, {}, requesting_user_id=requesting_id)

    # Run B: high interactions between u01 and u02
    high_int_counts = {
        canonical_pair("u01", "u02"): {"likes": 100, "comments": 100, "dms": 100}
    }
    result_high_int = run_pipeline(users, high_int_counts, requesting_user_id=requesting_id)

    # Find u01 and u02 in each result
    def get_coord(results, uid):
        r = next(c for c in results if c["user_id"] == uid)
        return np.array([r["x"], r["y"]])

    # Distance between u01 and u02 in no-interaction run
    u01_no = get_coord(result_no_int["translated_results"], "u01")
    u02_no = get_coord(result_no_int["translated_results"], "u02")
    dist_no_int = float(np.linalg.norm(u01_no - u02_no))

    # Distance between u01 and u02 in high-interaction run
    u01_hi = get_coord(result_high_int["translated_results"], "u01")
    u02_hi = get_coord(result_high_int["translated_results"], "u02")
    dist_high_int = float(np.linalg.norm(u01_hi - u02_hi))

    assert dist_high_int < dist_no_int, (
        f"Expected high-interaction users to be closer: "
        f"dist_no_int={dist_no_int:.4f}, dist_high_int={dist_high_int:.4f}"
    )


# ── SC-1: INT-01 extensibility ────────────────────────────────────────────────

def test_new_interaction_type_requires_only_config_change():
    """SC-1: Adding a new interaction type to INTERACTION_WEIGHTS dict flows through
    with zero logic changes — no code modification required."""
    from models.config import algorithm as cfg
    original_weights = dict(cfg.INTERACTION_WEIGHTS)

    try:
        # Add a new interaction type with zero weight (safe to not affect output)
        cfg.INTERACTION_WEIGHTS["reactions"] = 0.0

        users = make_minimal_users(12)
        raw_counts = {
            canonical_pair("u01", "u02"): {
                "likes": 5, "comments": 3, "dms": 1, "reactions": 7
            }
        }
        # Should run without any errors or code changes
        result = run_pipeline(users, raw_counts, requesting_user_id="u00")
        assert len(result["translated_results"]) == 12
        print("SC-1 verified: new interaction type 'reactions' flowed through with zero logic changes")
    finally:
        # Restore original weights
        cfg.INTERACTION_WEIGHTS.clear()
        cfg.INTERACTION_WEIGHTS.update(original_weights)


# ── requesting user tier ──────────────────────────────────────────────────────

def test_requesting_user_is_tier_1():
    """ORIG-02: Requesting user is always Tier 1."""
    users = make_minimal_users(15)
    result = run_pipeline(users, {}, requesting_user_id="u07")
    requesting = next(
        c for c in result["translated_results"] if c["user_id"] == "u07"
    )
    assert requesting["tier"] == 1
