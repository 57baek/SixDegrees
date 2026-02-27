from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from services.map_pipeline import scheduler
from services.map_pipeline import scheduler_lock
from services.map_pipeline.scheduler_lock import (
    DEFAULT_LOCK_TTL_SECONDS,
    acquire_global_compute_lock,
    release_global_compute_lock,
)


def _build_mock_supabase_with_payload(payload):
    mock_sb = MagicMock()
    mock_sb.rpc.return_value.execute.return_value = SimpleNamespace(data=payload)
    return mock_sb


def test_lock_acquire_success(monkeypatch):
    mock_sb = _build_mock_supabase_with_payload({"acquired": True})
    monkeypatch.setattr(
        "services.map_pipeline.scheduler_lock.get_supabase_client",
        lambda: mock_sb,
    )

    acquired, owner_token = acquire_global_compute_lock(owner_token="owner-1")

    assert acquired is True
    assert owner_token == "owner-1"
    mock_sb.rpc.assert_called_once_with(
        "acquire_global_compute_lock",
        {
            "p_lock_key": "map_pipeline_global_compute",
            "p_owner_token": "owner-1",
            "p_ttl_seconds": DEFAULT_LOCK_TTL_SECONDS,
        },
    )


def test_lock_contention_returns_false(monkeypatch):
    mock_sb = _build_mock_supabase_with_payload({"acquired": False})
    monkeypatch.setattr(
        "services.map_pipeline.scheduler_lock.get_supabase_client",
        lambda: mock_sb,
    )

    acquired, owner_token = acquire_global_compute_lock(owner_token="owner-2")

    assert acquired is False
    assert owner_token == "owner-2"


def test_lock_release_happens_on_success_and_error(monkeypatch):
    monkeypatch.setattr(
        "services.map_pipeline.scheduler_lock.acquire_global_compute_lock",
        lambda owner_token=None, ttl_seconds=DEFAULT_LOCK_TTL_SECONDS: (True, "owner-3"),
    )

    release_calls = []

    def fake_release(owner_token):
        release_calls.append(owner_token)
        return True

    monkeypatch.setattr(
        "services.map_pipeline.scheduler_lock.release_global_compute_lock",
        fake_release,
    )

    def run_with_lock(work):
        acquired, owner_token = scheduler_lock.acquire_global_compute_lock()
        if not acquired:
            return
        try:
            work()
        finally:
            scheduler_lock.release_global_compute_lock(owner_token)

    run_with_lock(lambda: None)

    with pytest.raises(RuntimeError, match="boom"):
        run_with_lock(lambda: (_ for _ in ()).throw(RuntimeError("boom")))

    assert release_calls == ["owner-3", "owner-3"]


def test_release_global_compute_lock_success(monkeypatch):
    mock_sb = _build_mock_supabase_with_payload({"released": True})
    monkeypatch.setattr(
        "services.map_pipeline.scheduler_lock.get_supabase_client",
        lambda: mock_sb,
    )

    released = release_global_compute_lock("owner-4")

    assert released is True
    mock_sb.rpc.assert_called_once_with(
        "release_global_compute_lock",
        {
            "p_lock_key": "map_pipeline_global_compute",
            "p_owner_token": "owner-4",
        },
    )


def test_setup_scheduler_registers_global_and_warm_only_jobs(monkeypatch):
    mock_sb = MagicMock()
    mock_sb.rpc.return_value.execute.return_value = SimpleNamespace(
        data=[{"timezone": "UTC"}, {"timezone": "America/New_York"}]
    )
    monkeypatch.setattr("services.map_pipeline.scheduler.get_supabase_client", lambda: mock_sb)

    captured_jobs = []

    class FakeScheduler:
        def add_job(self, func, trigger=None, args=None, id=None, replace_existing=None):
            captured_jobs.append(
                {
                    "func": func,
                    "trigger": trigger,
                    "args": args,
                    "id": id,
                    "replace_existing": replace_existing,
                }
            )

    monkeypatch.setattr("services.map_pipeline.scheduler.AsyncIOScheduler", FakeScheduler)
    monkeypatch.setattr(
        "services.map_pipeline.scheduler.CronTrigger",
        lambda **kwargs: kwargs,
    )

    configured_scheduler = scheduler.setup_scheduler()

    assert isinstance(configured_scheduler, FakeScheduler)
    assert len(captured_jobs) == 3

    global_job = next(job for job in captured_jobs if job["id"] == "global_compute_daily_utc")
    assert global_job["func"] is scheduler._run_daily_global_compute
    assert global_job["trigger"] == {"hour": 0, "minute": 0, "timezone": "UTC"}

    warm_jobs = [job for job in captured_jobs if job["id"].startswith("warm_only_")]
    assert {job["args"][0] for job in warm_jobs} == {"UTC", "America/New_York"}
    for warm_job in warm_jobs:
        assert warm_job["func"] is scheduler._run_warm_only_for_timezone
        assert warm_job["trigger"]["hour"] == 19
        assert warm_job["trigger"]["minute"] == 0


def test_warm_only_job_does_not_run_pipeline(monkeypatch):
    mock_sb = _build_mock_supabase_with_payload([{"id": "u1"}, {"id": "u2"}])
    monkeypatch.setattr("services.map_pipeline.scheduler.get_supabase_client", lambda: mock_sb)

    run_pipeline_mock = MagicMock()
    refresh_mock = MagicMock(return_value=False)
    monkeypatch.setattr("services.map_pipeline.scheduler.run_pipeline_for_user", run_pipeline_mock)
    monkeypatch.setattr("services.map_pipeline.scheduler.refresh_warm_payload_if_stale", refresh_mock)

    scheduler._run_warm_only_for_timezone("UTC")

    run_pipeline_mock.assert_not_called()
    assert refresh_mock.call_count == 2
    refresh_mock.assert_any_call("u1")
    refresh_mock.assert_any_call("u2")
    mock_sb.rpc.assert_called_once_with("get_profiles_by_timezone", {"p_timezone": "UTC"})


def test_dedupe_skips_global_compute_when_lock_not_acquired(monkeypatch):
    monkeypatch.setattr(
        "services.map_pipeline.scheduler.acquire_global_compute_lock",
        lambda ttl_seconds=DEFAULT_LOCK_TTL_SECONDS: (False, "owner-x"),
    )

    run_pipeline_mock = MagicMock()
    release_mock = MagicMock()
    monkeypatch.setattr("services.map_pipeline.scheduler.run_pipeline_for_user", run_pipeline_mock)
    monkeypatch.setattr("services.map_pipeline.scheduler.release_global_compute_lock", release_mock)

    scheduler._run_daily_global_compute()

    run_pipeline_mock.assert_not_called()
    release_mock.assert_not_called()


def test_dedupe_releases_lock_on_global_compute_error(monkeypatch):
    monkeypatch.setattr(
        "services.map_pipeline.scheduler.acquire_global_compute_lock",
        lambda ttl_seconds=DEFAULT_LOCK_TTL_SECONDS: (True, "owner-y"),
    )
    monkeypatch.setattr(
        "services.map_pipeline.scheduler._select_global_compute_user_id",
        lambda: "u-anchor",
    )

    release_mock = MagicMock(return_value=True)
    monkeypatch.setattr("services.map_pipeline.scheduler.release_global_compute_lock", release_mock)
    monkeypatch.setattr(
        "services.map_pipeline.scheduler.run_pipeline_for_user",
        lambda user_id: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    with pytest.raises(RuntimeError, match="boom"):
        scheduler._run_daily_global_compute()

    release_mock.assert_called_once_with("owner-y")
