"""Test configuration for FastAPI endpoint tests.

Provides:
- mock_sb: a MagicMock replacing the Supabase client for all HTTP tests
- client: TestClient with get_current_user overridden + Supabase mocked
- client_no_auth: TestClient with real get_current_user (triggers 401 on missing token)
"""

import sys
import os
import pytest
from unittest.mock import MagicMock, patch
from starlette.testclient import TestClient

# Ensure backend root is on sys.path so imports resolve from backend/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from routes.deps import get_current_user

TEST_USER_ID = "test-user-uuid"

_MOCK_PROFILE_ROW = {
    "id": TEST_USER_ID,
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


def _build_mock_supabase() -> MagicMock:
    """Build a MagicMock Supabase client with realistic chained return values."""
    mock_sb = MagicMock()

    # rpc() calls are routed by function name via side_effect so that:
    # - get_global_map_coordinates returns deterministic map rows for map contract tests.
    # - get_profile_nicknames returns nickname rows matching the map result IDs.
    # - get_all_interactions returns [] (no interaction rows — avoids KeyError on
    #   user_id_a/user_id_b when pipeline iterates interaction rows).
    # - All other rpc() calls (get_profile, get_all_profiles, upsert_profile,
    #   get_distinct_timezones, etc.) return execute().data = [_MOCK_PROFILE_ROW].
    # Tests that need to override the return data should set mock_sb.rpc.side_effect = None
    # and then assign mock_sb.rpc.return_value.execute.return_value.data directly.
    _empty_result = MagicMock()
    _empty_result.execute.return_value.data = []

    _map_result = MagicMock()
    _map_result.execute.return_value.data = [
        {
            "user_id": TEST_USER_ID,
            "x": 0.0,
            "y": 0.0,
            "prev_x": None,
            "prev_y": None,
            "computed_at": "2026-02-26T00:00:00Z",
            "version_date": "2026-02-26",
        }
    ]

    _nickname_result = MagicMock()
    _nickname_result.execute.return_value.data = [{"id": TEST_USER_ID, "nickname": "Test User"}]

    _default_result = MagicMock()
    _default_result.execute.return_value.data = [_MOCK_PROFILE_ROW]

    # Store default result on return_value so tests can inspect call_args_list.
    mock_sb.rpc.return_value = _default_result

    def _rpc_side_effect(fn_name, *args, **kwargs):
        if fn_name == "get_global_map_coordinates":
            return _map_result
        if fn_name == "get_profile_nicknames":
            return _nickname_result
        if fn_name == "get_all_interactions":
            return _empty_result
        return _default_result

    mock_sb.rpc.side_effect = _rpc_side_effect

    return mock_sb


@pytest.fixture
def mock_sb():
    """Yield a MagicMock Supabase client and patch it into config.supabase.supabase."""
    _mock = _build_mock_supabase()
    with patch("config.supabase.supabase", _mock):
        yield _mock


@pytest.fixture
def client(mock_sb):
    """TestClient with dependency override for get_current_user and mocked Supabase.

    Also patches setup_scheduler to prevent APScheduler from starting in tests.
    """
    with patch("services.map_pipeline.scheduler.setup_scheduler", return_value=MagicMock()):
        app.dependency_overrides[get_current_user] = lambda: TEST_USER_ID
        with TestClient(app, raise_server_exceptions=False) as tc:
            yield tc
        app.dependency_overrides.clear()


@pytest.fixture
def client_no_auth():
    """TestClient WITHOUT dependency override so real get_current_user runs.

    For no-auth requests (no Authorization header), credentials=None triggers
    the 401 path inside get_current_user immediately — no Supabase call needed.
    Supabase is still mocked to prevent network calls during app startup/lifespan.
    """
    _mock = _build_mock_supabase()
    with patch("config.supabase.supabase", _mock):
        with patch("services.map_pipeline.scheduler.setup_scheduler", return_value=MagicMock()):
            app.dependency_overrides.clear()
            with TestClient(app, raise_server_exceptions=False) as tc:
                yield tc
            app.dependency_overrides.clear()
