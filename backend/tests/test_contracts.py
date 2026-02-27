"""Contract tests: verify all v1.1 endpoints return correct status + response shape.

These tests document the API contract each endpoint must honor so future changes
can be verified automatically. They run against a mocked Supabase client so no
real database or network calls are made.
"""
from unittest.mock import MagicMock, patch

import pytest


# ── GET /map/{user_id} ────────────────────────────────────────────────────

def test_get_map_response_shape(client):
    """GET /map/{user_id} keeps compatibility keys and adds suggestion metadata."""
    response = client.get("/map/test-user-uuid")
    assert response.status_code == 200
    data = response.json()
    assert "user_id" in data
    assert "version_date" in data
    assert "computed_at" in data
    assert "coordinates" in data
    assert isinstance(data["coordinates"], list)
    coord = data["coordinates"][0]
    assert all(k in coord for k in ("user_id", "x", "y", "tier", "nickname", "is_suggestion"))


def test_get_map_other_user_returns_403(client):
    """GET /map/{user_id} for another user returns 403 (self-only guard)."""
    response = client.get("/map/other-user-uuid")
    assert response.status_code == 403


def test_get_map_requester_origin_and_mutual_primarys(client):
    """GET /map/{user_id} anchors requester and marks only fallback as suggestions."""
    response = client.get("/map/test-user-uuid")
    assert response.status_code == 200
    data = response.json()

    by_id = {row["user_id"]: row for row in data["coordinates"]}
    requester = by_id["test-user-uuid"]
    assert requester["x"] == pytest.approx(0.0)
    assert requester["y"] == pytest.approx(0.0)
    assert requester["is_suggestion"] is False

    mutual = by_id["mutual-user-uuid"]
    assert mutual["is_suggestion"] is False
    assert mutual["x"] == pytest.approx(4.0)
    assert mutual["y"] == pytest.approx(6.0)

    suggestion_nodes = [row for row in data["coordinates"] if row["is_suggestion"]]
    assert suggestion_nodes
    assert all(node["user_id"] != "test-user-uuid" for node in suggestion_nodes)


def test_map_contract_profiles_only(client, mock_sb):
    """GET /map/{user_id} uses only profiles-era RPCs (no legacy user_profiles reads)."""
    response = client.get("/map/test-user-uuid")
    assert response.status_code == 200

    rpc_names = [call.args[0] for call in mock_sb.rpc.call_args_list if call.args]
    assert "get_global_map_coordinates" in rpc_names
    assert "get_ego_map_profiles" in rpc_names
    assert "get_profile" not in rpc_names
    assert all("user_profiles" not in str(call) for call in mock_sb.rpc.call_args_list)


def test_get_map_returns_503_when_profile_projection_missing(client, mock_sb):
    """GET /map/{user_id} fails closed when coordinate users lack profile projection rows."""

    original_side_effect = mock_sb.rpc.side_effect
    incomplete_projection = MagicMock()
    incomplete_projection.execute.return_value.data = [
        {
            "id": "test-user-uuid",
            "nickname": "Test User",
            "friends": ["mutual-user-uuid"],
        }
    ]

    def _rpc_side_effect(name, *args, **kwargs):
        if name == "get_ego_map_profiles":
            return incomplete_projection
        return original_side_effect(name, *args, **kwargs)

    # Keep coordinate rows from fixture defaults and return incomplete profile projection.
    mock_sb.rpc.side_effect = _rpc_side_effect

    response = client.get("/map/test-user-uuid")
    assert response.status_code == 503
    assert "profile projection is incomplete" in response.json()["detail"]


def test_get_map_no_jwt_returns_401(client_no_auth):
    """GET /map/{user_id} without JWT returns 401 (Phase 7 BEND-06)."""
    response = client_no_auth.get("/map/some-user-uuid")
    assert response.status_code == 401


def test_map_trigger_no_jwt_returns_401(client_no_auth):
    """POST /map/trigger/{user_id} without JWT returns 401 (Phase 7 BEND-06)."""
    response = client_no_auth.post("/map/trigger/some-user-uuid")
    assert response.status_code == 401


# ── POST /map/trigger/{user_id} ───────────────────────────────────────────

def test_post_map_trigger_returns_non_500(client):
    """POST /map/trigger/{user_id} never returns 500 — either 200 or 422 (pipeline error).

    The pipeline fails with 422 (ValueError: requesting_user_id not found) when
    there are not enough users in the mocked Supabase — correct behavior.
    """
    response = client.post("/map/trigger/test-user-uuid")
    assert response.status_code in (200, 422)
    assert response.status_code != 500


def test_post_map_trigger_other_user_returns_403(client):
    """POST /map/trigger/{user_id} for another user returns 403 (self-only guard)."""
    response = client.post("/map/trigger/other-user-uuid")
    assert response.status_code == 403


def test_post_map_trigger_success_keeps_map_metadata_contract(client):
    """POST /map/trigger/{user_id} success still returns map metadata fields."""
    with patch("routes.map.run_pipeline_for_user", return_value=None):
        response = client.post("/map/trigger/test-user-uuid")
    assert response.status_code == 200
    data = response.json()
    assert "version_date" in data
    assert "computed_at" in data
    assert isinstance(data.get("coordinates"), list)


# ── POST /interactions/* ─────────────────────────────────────────────────

def test_interactions_like_contract(client):
    """POST /interactions/like returns 200 with {detail: 'likes recorded'}."""
    response = client.post("/interactions/like", json={"target_user_id": "other-user-uuid"})
    assert response.status_code == 200
    data = response.json()
    assert data.get("detail") == "likes recorded"


def test_interactions_like_contract_calls_increment_rpc_with_canonical_pair(client, mock_sb):
    """POST /interactions/like calls increment_interaction with canonical uid ordering."""
    response = client.post("/interactions/like", json={"target_user_id": "aaa-user-uuid"})
    assert response.status_code == 200

    increment_calls = [
        call
        for call in mock_sb.rpc.call_args_list
        if call.args and call.args[0] == "increment_interaction"
    ]
    assert increment_calls

    payload = increment_calls[-1].args[1]
    assert payload["p_user_id_a"] == "aaa-user-uuid"
    assert payload["p_user_id_b"] == "test-user-uuid"
    assert payload["p_column"] == "likes_count"


def test_interactions_comment_contract(client):
    """POST /interactions/comment returns 200 with {detail: 'comments recorded'}."""
    response = client.post("/interactions/comment", json={"target_user_id": "other-user-uuid"})
    assert response.status_code == 200
    data = response.json()
    assert data.get("detail") == "comments recorded"


def test_interactions_comment_contract_calls_increment_rpc(client, mock_sb):
    """POST /interactions/comment increments the expected interactions column."""
    response = client.post("/interactions/comment", json={"target_user_id": "other-user-uuid"})
    assert response.status_code == 200

    increment_calls = [
        call
        for call in mock_sb.rpc.call_args_list
        if call.args and call.args[0] == "increment_interaction"
    ]
    assert increment_calls
    assert increment_calls[-1].args[1]["p_column"] == "comments_count"


def test_interactions_dm_returns_dms_recorded(client):
    """POST /interactions/dm returns 200 with {detail: 'dms recorded'} — not 'dm recorded'.

    This test verifies the BEND-04 bug fix: response was 'dm recorded' (wrong),
    must now be 'dms recorded' (correct). The fix was applied in Phase 7 via
    _RESPONSE_LABELS dict in routes/interactions.py.
    """
    response = client.post("/interactions/dm", json={"target_user_id": "other-user-uuid"})
    assert response.status_code == 200
    data = response.json()
    assert data.get("detail") == "dms recorded", (
        f"Expected 'dms recorded' but got '{data.get('detail')}'. "
        "BEND-04 fix may not be applied."
    )


def test_interactions_self_returns_400(client, mock_sb):
    """POST /interactions/* with self as target returns 400 and skips RPC write."""
    # client fixture sets acting user to "test-user-uuid"
    response = client.post("/interactions/like", json={"target_user_id": "test-user-uuid"})
    assert response.status_code == 400

    increment_calls = [
        call
        for call in mock_sb.rpc.call_args_list
        if call.args and call.args[0] == "increment_interaction"
    ]
    assert not increment_calls


def test_interactions_no_jwt_returns_401(client_no_auth):
    """POST /interactions/* without JWT returns 401."""
    response = client_no_auth.post("/interactions/like", json={"target_user_id": "other-uuid"})
    assert response.status_code == 401


# ── PUT /profile ──────────────────────────────────────────────────────────

def test_put_profile_contract(client):
    """PUT /profile with valid JWT and body returns 200."""
    response = client.put("/profile", json={"nickname": "Contract Test"})
    assert response.status_code == 200


def test_put_profile_no_jwt_returns_401(client_no_auth):
    """PUT /profile without JWT returns 401."""
    response = client_no_auth.put("/profile", json={"nickname": "Should Fail"})
    assert response.status_code == 401


# ── GET /match ───────────────────────────────────────────────────────────

def test_get_match_happy_path(client, mock_sb):
    """GET /match with valid JWT returns 200 with matches list and correct shape.

    Overrides the Supabase select mock to return two user rows so the match
    endpoint can find the acting user and compute at least one similarity score.
    """
    from unittest.mock import patch

    _OTHER_USER_ROW = {
        "id": "other-user-uuid",
        "nickname": "Other User",
        "is_onboarded": True,
        "interests": ["hiking"],
        "city": "LA",
        "state": "CA",
        "age": 30,
        "languages": ["English"],
        "education": "Biology",
        "industry": "Health",
        "timezone": "UTC",
        "occupation": None,
    }
    _ACTING_USER_ROW = {
        "id": "test-user-uuid",
        "nickname": "Test User",
        "is_onboarded": True,
        "interests": ["coding"],
        "city": "SF",
        "state": "CA",
        "age": 25,
        "languages": ["English"],
        "education": "CS",
        "industry": "Tech",
        "timezone": "UTC",
        "occupation": None,
    }
    # Clear side_effect so return_value takes effect for all rpc() calls in this test.
    mock_sb.rpc.side_effect = None
    mock_sb.rpc.return_value.execute.return_value.data = [_ACTING_USER_ROW, _OTHER_USER_ROW]

    response = client.get("/match")
    assert response.status_code == 200
    data = response.json()
    assert "matches" in data
    assert isinstance(data["matches"], list)
    assert len(data["matches"]) >= 1
    match_item = data["matches"][0]
    assert "user_id" in match_item
    assert "nickname" in match_item
    assert "similarity_score" in match_item
    assert isinstance(match_item["similarity_score"], float)
