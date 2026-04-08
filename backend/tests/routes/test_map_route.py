"""Comprehensive route tests for GET /map/{user_id} and POST /map/trigger/{user_id}.

Mocks at the service level (build_ego_map, pipeline.run) rather than Supabase
to test routing logic independently of pipeline implementation details.
"""
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from services.map.contracts import EgoMapNode, EgoMapResponse, PipelineResult

_COMPUTED_AT = "2026-03-27T00:00:00Z"

_MOCK_EGO_RESPONSE = EgoMapResponse(
    coordinates=[
        EgoMapNode(
            user_id="other-user-uuid",
            nickname="Other User",
            avatar_url=None,
            x=3.0,
            y=4.0,
            tier=1,
        )
    ],
    computed_at=_COMPUTED_AT,
)

_MOCK_PIPELINE_RESULT = PipelineResult(
    user_ids=["test-user-uuid"],
    coords=np.zeros((1, 2)),
    edge_count=0,
    duration_ms=100,
)


# ── GET /map/{user_id} ────────────────────────────────────────────────────

def test_get_map_200_response_shape(client):
    """GET /map/{user_id} returns 200 with computed_at and coordinates list."""
    with patch("routes.map.build_ego_map", return_value=_MOCK_EGO_RESPONSE):
        response = client.get("/map/test-user-uuid")
    assert response.status_code == 200
    data = response.json()
    assert "computed_at" in data
    assert "coordinates" in data
    assert isinstance(data["coordinates"], list)
    assert data["computed_at"] == _COMPUTED_AT


def test_get_map_coordinates_shape(client):
    """GET /map/{user_id} coordinate items have required fields."""
    with patch("routes.map.build_ego_map", return_value=_MOCK_EGO_RESPONSE):
        response = client.get("/map/test-user-uuid")
    assert response.status_code == 200
    coord = response.json()["coordinates"][0]
    assert all(k in coord for k in ("user_id", "x", "y", "tier", "nickname"))


def test_get_map_403_wrong_user(client):
    """GET /map/{user_id} for a different user_id returns 403."""
    response = client.get("/map/other-user-uuid")
    assert response.status_code == 403
    assert "You may only view your own map" in response.json()["detail"]


def test_get_map_404_user_not_in_positions(client):
    """GET /map/{user_id} returns 404 when build_ego_map raises HTTPException 404."""
    from fastapi import HTTPException

    with patch(
        "routes.map.build_ego_map",
        side_effect=HTTPException(status_code=404, detail="Map not yet computed for this user"),
    ):
        response = client.get("/map/test-user-uuid")
    assert response.status_code == 404
    assert "Map not yet computed" in response.json()["detail"]


def test_get_map_401_no_jwt(client_no_auth):
    """GET /map/{user_id} without JWT returns 401."""
    response = client_no_auth.get("/map/test-user-uuid")
    assert response.status_code == 401


# ── POST /map/trigger/{user_id} ───────────────────────────────────────────

def test_post_map_trigger_200(client):
    """POST /map/trigger/{user_id} returns 200 with status and computed_at."""
    mock_positions = MagicMock()
    mock_positions.execute.return_value.data = [{"computed_at": _COMPUTED_AT}]

    with patch("routes.map.run", return_value=_MOCK_PIPELINE_RESULT):
        with patch("routes.map.get_supabase_client") as mock_get_sb:
            mock_sb = MagicMock()
            mock_sb.table.return_value.select.return_value.limit.return_value.execute.return_value.data = [
                {"computed_at": _COMPUTED_AT}
            ]
            mock_get_sb.return_value = mock_sb
            response = client.post("/map/trigger/test-user-uuid")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "computed_at" in data
    assert data["computed_at"] == _COMPUTED_AT


def test_post_map_trigger_503_on_pipeline_failure(client):
    """POST /map/trigger/{user_id} returns 503 when pipeline.run() raises."""
    with patch("routes.map.run", side_effect=RuntimeError("pipeline exploded")):
        response = client.post("/map/trigger/test-user-uuid")
    assert response.status_code == 503
    assert "pipeline exploded" in response.json()["detail"]


def test_post_map_trigger_401_no_jwt(client_no_auth):
    """POST /map/trigger/{user_id} without JWT returns 401."""
    response = client_no_auth.post("/map/trigger/test-user-uuid")
    assert response.status_code == 401


def test_post_map_trigger_403_wrong_user(client):
    """POST /map/trigger/{user_id} for a different user_id returns 403."""
    response = client.post("/map/trigger/other-user-uuid")
    assert response.status_code == 403
    assert "You may only trigger your own map" in response.json()["detail"]


def test_post_map_trigger_computed_at_none_when_no_rows(client):
    """POST /map/trigger/{user_id} returns computed_at=None when user_positions is empty."""
    with patch("routes.map.run", return_value=_MOCK_PIPELINE_RESULT):
        with patch("routes.map.get_supabase_client") as mock_get_sb:
            mock_sb = MagicMock()
            mock_sb.table.return_value.select.return_value.limit.return_value.execute.return_value.data = []
            mock_get_sb.return_value = mock_sb
            response = client.post("/map/trigger/test-user-uuid")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["computed_at"] is None
