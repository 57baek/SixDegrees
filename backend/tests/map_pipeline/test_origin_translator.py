"""Tests for origin_translator.translate_and_assign_tiers()"""
import numpy as np
import pytest
from services.map_pipeline.origin_translator import translate_and_assign_tiers


def make_coords(n: int, seed: int = 42) -> np.ndarray:
    """Create n random 2D coordinates."""
    rng = np.random.default_rng(seed)
    return rng.random((n, 2)) * 10.0  # scale up to avoid all-near-origin


# ── ORIG-01: requesting user at (0, 0) after translation ────────────────────

def test_requesting_user_at_origin():
    """ORIG-01: After translation, requesting user is at exactly (0.0, 0.0)."""
    user_ids = ["u0", "u1", "u2", "u3", "u4", "u5", "u6", "u7", "u8", "u9", "u10"]
    coords = make_coords(len(user_ids))
    results = translate_and_assign_tiers(user_ids, coords, requesting_user_id="u3")
    requesting = next(r for r in results if r["user_id"] == "u3")
    assert requesting["x"] == pytest.approx(0.0, abs=1e-10)
    assert requesting["y"] == pytest.approx(0.0, abs=1e-10)


def test_all_users_translated_consistently():
    """ORIG-01: All other users' coordinates shift by the same offset."""
    user_ids = [f"u{i}" for i in range(10)]
    coords = make_coords(10)
    requesting_idx = 2
    offset = coords[requesting_idx].copy()

    results = translate_and_assign_tiers(user_ids, coords, requesting_user_id="u2")

    for r in results:
        i = user_ids.index(r["user_id"])
        expected_x = float(coords[i][0] - offset[0])
        expected_y = float(coords[i][1] - offset[1])
        assert r["x"] == pytest.approx(expected_x, abs=1e-10)
        assert r["y"] == pytest.approx(expected_y, abs=1e-10)


# ── ORIG-02: requesting user included at (0,0) as Tier 1 ─────────────────────

def test_requesting_user_in_output():
    """ORIG-02: Requesting user must appear in output results."""
    user_ids = [f"u{i}" for i in range(12)]
    coords = make_coords(12)
    results = translate_and_assign_tiers(user_ids, coords, requesting_user_id="u5")
    result_ids = [r["user_id"] for r in results]
    assert "u5" in result_ids


def test_requesting_user_is_tier_1():
    """ORIG-02: Requesting user is always Tier 1 (at origin, distance 0)."""
    user_ids = [f"u{i}" for i in range(12)]
    coords = make_coords(12)
    results = translate_and_assign_tiers(user_ids, coords, requesting_user_id="u0")
    requesting = next(r for r in results if r["user_id"] == "u0")
    assert requesting["tier"] == 1


def test_output_contains_all_users():
    """ORIG-02: All users (including requesting user) appear in output."""
    user_ids = [f"u{i}" for i in range(10)]
    coords = make_coords(10)
    results = translate_and_assign_tiers(user_ids, coords, requesting_user_id="u0")
    assert len(results) == 10
    result_ids = {r["user_id"] for r in results}
    assert result_ids == set(user_ids)


# ── ORIG-02: tier assignment ────────────────────────────────────────────────

def test_tier_1_count():
    """ORIG-02: Exactly 5 non-requesting users are Tier 1 (when N > 6)."""
    user_ids = [f"u{i}" for i in range(20)]
    coords = make_coords(20)
    results = translate_and_assign_tiers(user_ids, coords, requesting_user_id="u0")
    tier1_others = [r for r in results if r["tier"] == 1 and r["user_id"] != "u0"]
    assert len(tier1_others) == 5, f"Expected 5 Tier 1 non-requesting users, got {len(tier1_others)}"


def test_tier_2_range():
    """ORIG-02: Tier 2 covers ranks 6-15 (up to 10 users when enough exist)."""
    user_ids = [f"u{i}" for i in range(20)]
    coords = make_coords(20)
    results = translate_and_assign_tiers(user_ids, coords, requesting_user_id="u0")
    tier2 = [r for r in results if r["tier"] == 2]
    # With 20 users: 1 requesting + 5 tier1 + 10 tier2 + 4 tier3 (or fewer if beyond 0.75)
    assert len(tier2) <= 10


def test_tier_values_are_valid():
    """All tier values must be 1, 2, or 3."""
    user_ids = [f"u{i}" for i in range(15)]
    coords = make_coords(15)
    results = translate_and_assign_tiers(user_ids, coords, requesting_user_id="u7")
    for r in results:
        assert r["tier"] in (1, 2, 3), f"Invalid tier {r['tier']} for user {r['user_id']}"


# ── ORIG-03: stateless, per-requesting-user ──────────────────────────────────

def test_different_requesting_users_produce_different_origins():
    """ORIG-03: Each requesting user gets their own coordinate set — stateless function."""
    user_ids = [f"u{i}" for i in range(10)]
    coords = make_coords(10)

    results_u0 = translate_and_assign_tiers(user_ids, coords, requesting_user_id="u0")
    results_u1 = translate_and_assign_tiers(user_ids, coords, requesting_user_id="u1")

    # u2's coordinates should differ between the two runs (different origins)
    u2_in_u0_view = next(r for r in results_u0 if r["user_id"] == "u2")
    u2_in_u1_view = next(r for r in results_u1 if r["user_id"] == "u2")
    assert u2_in_u0_view["x"] != pytest.approx(u2_in_u1_view["x"], abs=1e-6), \
        "Same x for u2 from different requesting users — translation not applied per-user"


# ── output structure ─────────────────────────────────────────────────────────

def test_result_has_required_keys():
    """Each result dict has user_id, x, y, tier keys."""
    user_ids = [f"u{i}" for i in range(10)]
    coords = make_coords(10)
    results = translate_and_assign_tiers(user_ids, coords, requesting_user_id="u0")
    for r in results:
        assert "user_id" in r
        assert "x" in r
        assert "y" in r
        assert "tier" in r
