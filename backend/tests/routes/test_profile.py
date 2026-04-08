"""Unit tests for Phase 7 backend additions (updated for profiles migration).

Covers:
  TEST-01-A: GET /profile authenticated → 200 with profile fields including is_onboarded
  TEST-01-B: GET /profile no JWT → 401
  TEST-01-C: PUT /profile upsert payload includes is_onboarded=True
  TEST-01-E: GET /match no JWT → 401
"""


def test_get_profile_authenticated(client):
    """GET /profile with valid JWT returns 200 + profile fields including is_onboarded."""
    response = client.get("/profile")
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert "is_onboarded" in data


def test_get_profile_no_jwt(client_no_auth):
    """GET /profile with no Authorization header returns 401."""
    response = client_no_auth.get("/profile")
    assert response.status_code == 401


def test_put_profile_sets_is_onboarded(client, mock_sb):
    """PUT /profile upsert payload includes is_onboarded=True sent to Supabase."""
    response = client.put("/profile", json={"nickname": "Test User"})
    assert response.status_code == 200

    # Find the rpc("upsert_profile", ...) call and verify is_onboarded=True in p_data
    rpc_calls = [c for c in mock_sb.rpc.call_args_list if c[0][0] == "upsert_profile"]
    assert len(rpc_calls) == 1, f"Expected one rpc('upsert_profile') call, got: {mock_sb.rpc.call_args_list}"
    p_data = rpc_calls[0][0][1]["p_data"]
    assert p_data.get("is_onboarded") is True, (
        f"Expected is_onboarded=True in upsert_profile p_data, got: {p_data}"
    )


def test_match_no_jwt_returns_401(client_no_auth):
    """GET /match with no JWT returns 401 (Phase 7 creates and secures this route)."""
    response = client_no_auth.get("/match")
    assert response.status_code == 401


def test_get_profile_not_found(client, mock_sb):
    """GET /profile returns 404 when RPC returns empty data."""
    mock_sb.rpc.side_effect = None
    mock_sb.rpc.return_value.execute.return_value.data = []
    resp = client.get("/profile")
    assert resp.status_code == 404
    assert "Profile not found" in resp.json()["detail"]


def test_put_profile_interest_normalization(client, mock_sb):
    """PUT /profile deduplicates and lowercases interests."""
    mock_sb.rpc.side_effect = None
    mock_sb.rpc.return_value.execute.return_value.data = [{}]
    resp = client.put("/profile", json={"interests": ["Hiking", "hiking", " HIKING ", "coding"]})
    assert resp.status_code == 200
    # Verify upsert_profile was called with normalized interests
    call_args = mock_sb.rpc.call_args_list
    upsert_call = next(c for c in call_args if c[0][0] == "upsert_profile")
    interests = upsert_call[0][1]["p_data"]["interests"]
    assert interests == ["hiking", "coding"]


def test_put_profile_empty_interest_strings_skipped(client, mock_sb):
    """PUT /profile skips empty and whitespace-only interest strings."""
    mock_sb.rpc.side_effect = None
    mock_sb.rpc.return_value.execute.return_value.data = [{}]
    resp = client.put("/profile", json={"interests": ["  ", "", "coding"]})
    assert resp.status_code == 200
    call_args = mock_sb.rpc.call_args_list
    upsert_call = next(c for c in call_args if c[0][0] == "upsert_profile")
    interests = upsert_call[0][1]["p_data"]["interests"]
    assert interests == ["coding"]
