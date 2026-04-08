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
MUTUAL_USER_ID = "mutual-user-uuid"
ONE_WAY_USER_ID = "one-way-user-uuid"
SUGGESTION_USER_ID = "suggestion-user-uuid"

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
    # - get_all_interactions returns [] (no interaction rows — avoids KeyError on
    #   user_id_a/user_id_b when pipeline iterates interaction rows).
    # - All other rpc() calls (get_profile, get_all_profiles, upsert_profile,
    #   increment_interaction, etc.) return execute().data = [_MOCK_PROFILE_ROW].
    # Tests that need to override the return data should set mock_sb.rpc.side_effect = None
    # and then assign mock_sb.rpc.return_value.execute.return_value.data directly.
    _empty_result = MagicMock()
    _empty_result.execute.return_value.data = []

    _default_result = MagicMock()
    _default_result.execute.return_value.data = [_MOCK_PROFILE_ROW]

    # Store default result on return_value so tests can inspect call_args_list.
    mock_sb.rpc.return_value = _default_result

    def _rpc_side_effect(fn_name, *args, **kwargs):
        if fn_name == "get_all_interactions":
            return _empty_result
        return _default_result

    mock_sb.rpc.side_effect = _rpc_side_effect

    # Mock sb.table("user_positions") — used by build_ego_map and trigger route.
    _user_positions_result = MagicMock()
    _user_positions_result.execute.return_value.data = [
        {
            "user_id": TEST_USER_ID,
            "x": 10.0,
            "y": 5.0,
            "computed_at": "2026-02-26T00:00:00Z",
        },
        {
            "user_id": MUTUAL_USER_ID,
            "x": 14.0,
            "y": 11.0,
            "computed_at": "2026-02-26T00:00:00Z",
        },
        {
            "user_id": ONE_WAY_USER_ID,
            "x": 20.0,
            "y": 8.0,
            "computed_at": "2026-02-26T00:00:00Z",
        },
    ]

    # Mock sb.table("profiles") for build_ego_map — id/nickname/avatar_url columns.
    _profiles_result = MagicMock()
    _profiles_result.execute.return_value.data = [
        {"id": TEST_USER_ID, "nickname": "Test User", "avatar_url": None},
        {"id": MUTUAL_USER_ID, "nickname": "Mutual User", "avatar_url": None},
        {"id": ONE_WAY_USER_ID, "nickname": "One Way User", "avatar_url": None},
    ]

    # Route table() calls by table name.
    def _table_side_effect(table_name):
        tbl = MagicMock()
        if table_name == "user_positions":
            # Support both .select("*").execute() and .select("computed_at").limit(1).execute()
            tbl.select.return_value.execute.return_value = _user_positions_result.execute.return_value
            tbl.select.return_value.limit.return_value.execute.return_value = _user_positions_result.execute.return_value
        elif table_name == "profiles":
            tbl.select.return_value.execute.return_value = _profiles_result.execute.return_value
            # Support chained .eq() for profile lookups
            tbl.select.return_value.eq.return_value.execute.return_value = _profiles_result.execute.return_value
        else:
            # Generic table mock for upsert, update, insert, etc.
            tbl.select.return_value.execute.return_value.data = [_MOCK_PROFILE_ROW]
            tbl.select.return_value.eq.return_value.execute.return_value.data = [_MOCK_PROFILE_ROW]
            tbl.upsert.return_value.execute.return_value.data = []
            tbl.update.return_value.eq.return_value.execute.return_value.data = []
            tbl.insert.return_value.execute.return_value.data = []
        return tbl

    mock_sb.table.side_effect = _table_side_effect

    return mock_sb


@pytest.fixture
def mock_sb():
    """Yield a MagicMock Supabase client and patch it into config.settings._client."""
    _mock = _build_mock_supabase()
    with patch("config.settings._client", _mock):
        yield _mock


@pytest.fixture
def client(mock_sb):
    """TestClient with dependency override for get_current_user and mocked Supabase.

    Also patches setup_scheduler to prevent APScheduler from starting in tests.
    """
    with patch("services.map.scheduler.setup_scheduler", return_value=MagicMock()):
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
    with patch("config.settings._client", _mock):
        with patch("services.map.scheduler.setup_scheduler", return_value=MagicMock()):
            app.dependency_overrides.clear()
            with TestClient(app, raise_server_exceptions=False) as tc:
                yield tc
            app.dependency_overrides.clear()
