"""Tests for services/map/writer.py — normalization behavior."""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from services.map.writer import write


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_mock_sb(prev_rows: list[dict] = None) -> MagicMock:
    mock_sb = MagicMock()
    mock_sb.table("user_positions").select(
        "user_id,x,y"
    ).execute.return_value.data = prev_rows or []
    return mock_sb


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_coordinates_normalized_to_unit_square():
    """Output coordinates are normalized to [0, 1] regardless of raw UMAP range."""
    mock_sb = make_mock_sb()
    user_ids = ["uid-a", "uid-b", "uid-c"]
    new_coords = np.array([[0.0, 0.0], [5.0, 10.0], [10.0, 5.0]])

    with patch("config.settings._client", mock_sb):
        write(user_ids, new_coords)

    rows = {r["user_id"]: r for r in mock_sb.table("user_positions").upsert.call_args[0][0]}
    xs = [rows[uid]["x"] for uid in user_ids]
    ys = [rows[uid]["y"] for uid in user_ids]
    assert min(xs) == pytest.approx(0.0)
    assert max(xs) == pytest.approx(1.0)
    assert min(ys) == pytest.approx(0.0)
    assert max(ys) == pytest.approx(1.0)


def test_single_axis_range_zero_no_crash():
    """If all x-coords are identical, normalization uses 1.0 as range (no division by zero)."""
    mock_sb = make_mock_sb()
    user_ids = ["uid-a", "uid-b"]
    new_coords = np.array([[3.0, 0.0], [3.0, 10.0]])  # x range = 0

    with patch("config.settings._client", mock_sb):
        write(user_ids, new_coords)

    rows = {r["user_id"]: r for r in mock_sb.table("user_positions").upsert.call_args[0][0]}
    # x should be 0.0 for both (normalized by range=1 from value 3.0)
    assert rows["uid-a"]["x"] == pytest.approx(0.0)
    assert rows["uid-b"]["x"] == pytest.approx(0.0)
    # y should be normalized
    assert rows["uid-a"]["y"] == pytest.approx(0.0)
    assert rows["uid-b"]["y"] == pytest.approx(1.0)


def test_profile_change_reflects_fully_in_one_refresh():
    """After a total profile change, new positions are written in full without clamping."""
    # Previous positions at one extreme
    prev_rows = [
        {"user_id": "uid-1", "x": 0.0, "y": 0.0},
        {"user_id": "uid-2", "x": 1.0, "y": 1.0},
    ]
    mock_sb = make_mock_sb(prev_rows=prev_rows)
    user_ids = ["uid-1", "uid-2"]
    # New coords that would normalize to the opposite corner
    new_coords = np.array([[0.0, 0.0], [10.0, 10.0]])

    with patch("config.settings._client", mock_sb):
        write(user_ids, new_coords)

    rows = {r["user_id"]: r for r in mock_sb.table("user_positions").upsert.call_args[0][0]}
    assert rows["uid-1"]["x"] == pytest.approx(0.0)
    assert rows["uid-1"]["y"] == pytest.approx(0.0)
    assert rows["uid-2"]["x"] == pytest.approx(1.0)
    assert rows["uid-2"]["y"] == pytest.approx(1.0)


def test_upsert_called_with_correct_row_count():
    """upsert is called once with exactly one row per user."""
    mock_sb = make_mock_sb()
    user_ids = ["uid-1", "uid-2", "uid-3"]
    new_coords = np.array([[0.0, 0.0], [5.0, 5.0], [10.0, 10.0]])

    with patch("config.settings._client", mock_sb):
        write(user_ids, new_coords)

    upsert_call = mock_sb.table("user_positions").upsert
    upsert_call.assert_called_once()
    rows = upsert_call.call_args[0][0]
    assert len(rows) == 3
    assert {r["user_id"] for r in rows} == {"uid-1", "uid-2", "uid-3"}
