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

    # Verify Supabase upsert was called with is_onboarded=True in the payload
    upsert_call = mock_sb.table.return_value.upsert.call_args
    assert upsert_call is not None, "Expected upsert() to be called but it was not"
    upsert_payload = upsert_call[0][0]  # first positional argument to upsert()
    assert upsert_payload.get("is_onboarded") is True, (
        f"Expected is_onboarded=True in upsert payload, got: {upsert_payload}"
    )


def test_match_no_jwt_returns_401(client_no_auth):
    """GET /match with no JWT returns 401 (Phase 7 creates and secures this route)."""
    response = client_no_auth.get("/match")
    assert response.status_code == 401
