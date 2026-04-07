"""Tests for auth edge cases in routes/deps.py."""

from contextlib import contextmanager
from unittest.mock import MagicMock, patch
from starlette.testclient import TestClient
from supabase_auth.errors import AuthApiError

from app import app
from routes.deps import get_current_user


@contextmanager
def _client_with_real_auth(mock_sb):
    """TestClient that runs the real get_current_user (no dependency override)."""
    with patch("config.settings._client", mock_sb):
        with patch("services.map.scheduler.setup_scheduler", return_value=MagicMock()):
            app.dependency_overrides.clear()
            with TestClient(app, raise_server_exceptions=False) as tc:
                yield tc
            app.dependency_overrides.clear()


def test_invalid_token_returns_401():
    """get_user returns a response with user=None → 401."""
    mock_sb = MagicMock()
    mock_sb.auth.get_user.return_value = MagicMock(user=None)
    with _client_with_real_auth(mock_sb) as tc:
        resp = tc.get("/profile", headers={"Authorization": "Bearer bad-token"})
    assert resp.status_code == 401
    assert "Invalid or expired token" in resp.json()["detail"]


def test_get_user_returns_none_response_401():
    """get_user returns None directly (not a UserResponse object) → 401."""
    mock_sb = MagicMock()
    mock_sb.auth.get_user.return_value = None
    with _client_with_real_auth(mock_sb) as tc:
        resp = tc.get("/profile", headers={"Authorization": "Bearer bad-token"})
    assert resp.status_code == 401
    assert "Invalid or expired token" in resp.json()["detail"]


def test_auth_api_error_returns_401():
    """AuthApiError from get_user → 401."""
    mock_sb = MagicMock()
    mock_sb.auth.get_user.side_effect = AuthApiError("bad", 401, None)
    with _client_with_real_auth(mock_sb) as tc:
        resp = tc.get("/profile", headers={"Authorization": "Bearer bad-token"})
    assert resp.status_code == 401
    assert "Invalid or expired token" in resp.json()["detail"]
