"""Contract tests: verify all v1.1 endpoints return correct status + response shape.

These tests document the API contract each endpoint must honor so future changes
can be verified automatically. They run against a mocked Supabase client so no
real database or network calls are made.

Map route tests have been moved to tests/test_map_route.py.
"""
from unittest.mock import MagicMock, patch

import pytest


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

    Overrides the Supabase table mock to return two user rows so the match
    endpoint can find the acting user and compute at least one similarity score.
    """
    from unittest.mock import MagicMock

    _OTHER_USER_ROW = {
        "id": "other-user-uuid",
        "nickname": "Other User",
        "interests": ["hiking"],
        "city": "LA",
        "state": "CA",
        "age": 30,
        "languages": ["English"],
        "education": "Biology",
        "industry": "Health",
        "occupation": None,
    }
    _ACTING_USER_ROW = {
        "id": "test-user-uuid",
        "nickname": "Test User",
        "interests": ["coding"],
        "city": "SF",
        "state": "CA",
        "age": 25,
        "languages": ["English"],
        "education": "CS",
        "industry": "Tech",
        "occupation": None,
    }

    rows = [_ACTING_USER_ROW, _OTHER_USER_ROW]

    # Override the profiles table mock to return both rows for .select("*").execute()
    profiles_tbl = MagicMock()
    profiles_tbl.select.return_value.execute.return_value.data = rows
    profiles_tbl.select.return_value.eq.return_value.execute.return_value.data = rows

    original_side_effect = mock_sb.table.side_effect

    def _patched_table(table_name):
        if table_name == "profiles":
            return profiles_tbl
        return original_side_effect(table_name)

    mock_sb.table.side_effect = _patched_table

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
