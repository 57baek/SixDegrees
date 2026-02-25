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

    # GET /profile: sb.table("profiles").select("*").eq(uid).execute().data
    select_chain = mock_sb.table.return_value.select.return_value
    select_chain.eq.return_value.execute.return_value.data = [_MOCK_PROFILE_ROW]

    # PUT /profile: sb.table("profiles").upsert(...).execute()
    mock_sb.table.return_value.upsert.return_value.execute.return_value = MagicMock()

    # scheduler setup_scheduler queries: sb.table("profiles").select("timezone").execute().data
    # This is the same chain as above but returns empty list so no timezones are registered
    # The chain is shared via table().select() so we need a general fallback.
    # We override the select chain's execute to return empty data for the scheduler query.
    # Since the mock uses MagicMock, any unspecified chain returns a MagicMock (truthy).
    # We set data on the execute result explicitly above; the scheduler call (.select("timezone"))
    # shares the same mock chain and will also return [_MOCK_PROFILE_ROW] — that is fine
    # because setup_scheduler filters rows with row.get("timezone") which returns "UTC",
    # and will try to register a CronTrigger for "UTC". The scheduler mock (patched separately)
    # prevents actual APScheduler startup, so this is harmless.

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
