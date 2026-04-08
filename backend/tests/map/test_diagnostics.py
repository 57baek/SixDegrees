"""Tests for services/map/diagnostics.py."""

from unittest.mock import MagicMock, patch

from services.map.diagnostics import record_run


def make_mock_sb() -> MagicMock:
    return MagicMock()


def test_record_run_success():
    """record_run with status=success calls pipeline_runs.insert with correct payload."""
    mock_sb = make_mock_sb()
    with patch("config.settings._client", mock_sb):
        record_run("success", 100, 50, 1234, None)

    mock_sb.table("pipeline_runs").insert.assert_called_once_with({
        "status": "success",
        "user_count": 100,
        "edge_count": 50,
        "duration_ms": 1234,
        "error": None,
    })
    mock_sb.table("pipeline_runs").insert.return_value.execute.assert_called_once()


def test_record_run_failed_passes_error_field():
    """record_run with status=failed passes the error string through."""
    mock_sb = make_mock_sb()
    with patch("config.settings._client", mock_sb):
        record_run("failed", 0, 0, 500, "Something broke")

    mock_sb.table("pipeline_runs").insert.assert_called_once_with({
        "status": "failed",
        "user_count": 0,
        "edge_count": 0,
        "duration_ms": 500,
        "error": "Something broke",
    })


def test_record_run_skipped():
    """record_run with status=skipped writes status='skipped'."""
    mock_sb = make_mock_sb()
    with patch("config.settings._client", mock_sb):
        record_run("skipped", 0, 0, 0, None)

    call_args = mock_sb.table("pipeline_runs").insert.call_args[0][0]
    assert call_args["status"] == "skipped"
    assert call_args["error"] is None
