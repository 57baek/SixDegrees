"""Tests for services/map/ego.py — full Supabase version."""

import math
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from services.map.ego import build_ego_map

# ---------------------------------------------------------------------------
# Fixtures / constants
# ---------------------------------------------------------------------------

REQUESTER_ID = "user-a"
USER_B = "user-b"
USER_C = "user-c"
USER_D = "user-d"
COMPUTED_AT = "2026-03-27T00:00:00Z"

POSITIONS = [
    {"user_id": REQUESTER_ID, "x": 10.0, "y": 10.0, "computed_at": COMPUTED_AT},
    {"user_id": USER_B,       "x": 11.0, "y": 10.0, "computed_at": COMPUTED_AT},
    {"user_id": USER_C,       "x": 10.0, "y": 15.0, "computed_at": COMPUTED_AT},
    {"user_id": USER_D,       "x": 20.0, "y": 20.0, "computed_at": COMPUTED_AT},
]

PROFILES = [
    {"id": REQUESTER_ID, "nickname": "Alpha",   "avatar_url": "https://example.com/a.png"},
    {"id": USER_B,       "nickname": "Bravo",   "avatar_url": "https://example.com/b.png"},
    {"id": USER_C,       "nickname": "Charlie", "avatar_url": None},
    {"id": USER_D,       "nickname": "Delta",   "avatar_url": "https://example.com/d.png"},
]


def _make_mock_sb(positions=POSITIONS, profiles=PROFILES):
    """Return a mock Supabase client with user_positions and profiles wired up."""
    mock_sb = MagicMock()

    def _table(name):
        mock = MagicMock()
        if name == "user_positions":
            mock.select.return_value.execute.return_value.data = positions
        elif name == "profiles":
            mock.select.return_value.execute.return_value.data = profiles
        return mock

    mock_sb.table.side_effect = _table
    return mock_sb


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_requester_excluded_from_coordinates():
    """The requester's own node must not appear in result.coordinates."""
    mock_sb = _make_mock_sb()
    with patch("config.settings._client", mock_sb):
        response = build_ego_map(REQUESTER_ID)

    ids = [node.user_id for node in response.coordinates]
    assert REQUESTER_ID not in ids


def test_coordinate_translation():
    """user_b at (11,10) should be translated to (1.0, 0.0) relative to requester at (10,10)."""
    mock_sb = _make_mock_sb()
    with patch("config.settings._client", mock_sb):
        response = build_ego_map(REQUESTER_ID)

    node_b = next(n for n in response.coordinates if n.user_id == USER_B)
    assert node_b.x == pytest.approx(1.0)
    assert node_b.y == pytest.approx(0.0)


def test_tier_assignment():
    """With TIER1_K=5 and 3 other users (ranks 1,2,3), all should be tier=1."""
    mock_sb = _make_mock_sb()
    with patch("config.settings._client", mock_sb):
        response = build_ego_map(REQUESTER_ID)

    assert len(response.coordinates) == 3
    for node in response.coordinates:
        assert node.tier == 1, f"{node.user_id} has tier {node.tier}, expected 1"


def test_sorted_by_distance():
    """Nodes should be ordered: user_b (dist=1) < user_c (dist=5) < user_d (dist≈14.14)."""
    mock_sb = _make_mock_sb()
    with patch("config.settings._client", mock_sb):
        response = build_ego_map(REQUESTER_ID)

    ids = [node.user_id for node in response.coordinates]
    assert ids == [USER_B, USER_C, USER_D]


def test_computed_at():
    """result.computed_at should match the requester's row in user_positions."""
    mock_sb = _make_mock_sb()
    with patch("config.settings._client", mock_sb):
        response = build_ego_map(REQUESTER_ID)

    assert response.computed_at == COMPUTED_AT


def test_missing_avatar_url_is_none():
    """When a profile has avatar_url=None, EgoMapNode.avatar_url should be None."""
    mock_sb = _make_mock_sb()
    with patch("config.settings._client", mock_sb):
        response = build_ego_map(REQUESTER_ID)

    node_c = next(n for n in response.coordinates if n.user_id == USER_C)
    assert node_c.avatar_url is None


def test_404_when_requester_not_in_positions():
    """build_ego_map should raise HTTPException(404) if requester has no position row."""
    mock_sb = _make_mock_sb()
    with patch("config.settings._client", mock_sb):
        with pytest.raises(HTTPException) as exc_info:
            build_ego_map("nonexistent-user-id")

    assert exc_info.value.status_code == 404
