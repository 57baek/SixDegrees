"""Tests for services/map/scheduler._run_job behavior."""

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from services.map.scheduler import _run_job


def test_run_job_skipped_when_disabled_calls_record_run():
    """When GLOBAL_COMPUTE_ENABLED=False, _run_job calls record_run with status='skipped'."""
    mock_sb = MagicMock()
    with (
        patch("config.settings._client", mock_sb),
        patch("config.settings.GLOBAL_COMPUTE_ENABLED", False),
        patch("services.map.scheduler._settings.GLOBAL_COMPUTE_ENABLED", False),
    ):
        asyncio.run(_run_job())

    mock_sb.table("pipeline_runs").insert.assert_called_once_with({
        "status": "skipped",
        "user_count": 0,
        "edge_count": 0,
        "duration_ms": 0,
        "error": None,
    })


def test_run_job_skipped_does_not_call_pipeline_run():
    """When GLOBAL_COMPUTE_ENABLED=False, _run_job does NOT call pipeline.run()."""
    mock_sb = MagicMock()
    with (
        patch("config.settings._client", mock_sb),
        patch("services.map.scheduler._settings.GLOBAL_COMPUTE_ENABLED", False),
        patch("services.map.scheduler.pipeline.run") as mock_pipeline_run,
    ):
        asyncio.run(_run_job())

    mock_pipeline_run.assert_not_called()


def test_run_job_skips_when_lock_held(monkeypatch):
    """_run_job returns immediately without calling pipeline.run when lock is held."""
    import config.settings as cfg
    from services.map import scheduler as sched_mod
    from unittest.mock import MagicMock

    monkeypatch.setattr(cfg, "GLOBAL_COMPUTE_ENABLED", True)
    monkeypatch.setattr(sched_mod, "acquire_lock", lambda: False)

    mock_run = MagicMock()
    monkeypatch.setattr("services.map.pipeline.run", mock_run)

    asyncio.run(sched_mod._run_job())
    mock_run.assert_not_called()
