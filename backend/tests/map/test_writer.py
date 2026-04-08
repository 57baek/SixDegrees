"""Tests for services/map/writer.py — stability clip behavior."""

import math
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from config.settings import MAX_POSITION_DELTA
from services.map.writer import write


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_mock_sb(prev_rows: list[dict]) -> MagicMock:
    """Return a mock Supabase client seeded with the given previous rows."""
    mock_sb = MagicMock()
    # Wire up: sb.table("user_positions").select(...).execute().data
    mock_sb.table("user_positions").select(
        "user_id,x,y"
    ).execute.return_value.data = prev_rows
    return mock_sb


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_new_user_written_as_is():
    """No previous position: raw coordinates are written unchanged."""
    mock_sb = make_mock_sb(prev_rows=[])
    user_ids = ["uid-new"]
    new_coords = np.array([[3.0, 4.0]])

    with patch("config.settings._client", mock_sb):
        write(user_ids, new_coords)

    upsert_call = mock_sb.table("user_positions").upsert
    upsert_call.assert_called_once()
    rows = upsert_call.call_args[0][0]
    assert len(rows) == 1
    assert rows[0]["user_id"] == "uid-new"
    assert rows[0]["x"] == pytest.approx(3.0)
    assert rows[0]["y"] == pytest.approx(4.0)


def test_small_delta_not_clipped():
    """Delta ≤ MAX_POSITION_DELTA: position written as-is."""
    ox, oy = 0.0, 0.0
    # Move exactly MAX_POSITION_DELTA in x direction (boundary — must not clip)
    nx, ny = MAX_POSITION_DELTA, 0.0

    mock_sb = make_mock_sb(prev_rows=[{"user_id": "uid-a", "x": ox, "y": oy}])
    user_ids = ["uid-a"]
    new_coords = np.array([[nx, ny]])

    with patch("config.settings._client", mock_sb):
        write(user_ids, new_coords)

    rows = mock_sb.table("user_positions").upsert.call_args[0][0]
    assert rows[0]["x"] == pytest.approx(nx)
    assert rows[0]["y"] == pytest.approx(ny)


def test_large_delta_is_clipped():
    """Delta > MAX_POSITION_DELTA: clipped so distance from old to new == MAX_POSITION_DELTA."""
    ox, oy = 1.0, 1.0
    # Move far away — delta will be much larger than MAX_POSITION_DELTA
    nx, ny = 10.0, 10.0

    mock_sb = make_mock_sb(prev_rows=[{"user_id": "uid-b", "x": ox, "y": oy}])
    user_ids = ["uid-b"]
    new_coords = np.array([[nx, ny]])

    with patch("config.settings._client", mock_sb):
        write(user_ids, new_coords)

    rows = mock_sb.table("user_positions").upsert.call_args[0][0]
    cx, cy = rows[0]["x"], rows[0]["y"]
    clipped_delta = math.sqrt((cx - ox) ** 2 + (cy - oy) ** 2)
    assert clipped_delta == pytest.approx(MAX_POSITION_DELTA, rel=1e-6)


def test_upsert_called_with_correct_row_count():
    """upsert is called once with exactly one row per user."""
    prev_rows = [
        {"user_id": "uid-1", "x": 0.0, "y": 0.0},
        {"user_id": "uid-2", "x": 1.0, "y": 1.0},
    ]
    mock_sb = make_mock_sb(prev_rows=prev_rows)
    user_ids = ["uid-1", "uid-2", "uid-3"]
    new_coords = np.array([[0.1, 0.1], [1.1, 1.1], [5.0, 5.0]])

    with patch("config.settings._client", mock_sb):
        write(user_ids, new_coords)

    upsert_call = mock_sb.table("user_positions").upsert
    upsert_call.assert_called_once()
    rows = upsert_call.call_args[0][0]
    assert len(rows) == 3
    uids_written = {r["user_id"] for r in rows}
    assert uids_written == {"uid-1", "uid-2", "uid-3"}
