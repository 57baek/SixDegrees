import numpy as np
from datetime import datetime, timezone
from unittest.mock import patch

from models.user import UserProfile
from services.map_pipeline import run_pipeline_for_user


def _make_user(uid: str) -> UserProfile:
    return UserProfile(
        id=uid,
        nickname=uid,
        interests=["coding"],
        languages=["English"],
        city="SF",
        state="CA",
        education="CS",
        occupation="Engineer",
        industry="Tech",
        age=25,
        timezone="UTC",
    )


def test_failed_validation_blocks_publish():
    users = [_make_user(f"u{i:02d}") for i in range(10)]
    translated_results = [
        {"user_id": u.id, "x": float(i), "y": float(i), "tier": 1}
        for i, u in enumerate(users)
    ]

    with patch("services.map_pipeline.fetch_all", return_value=(users, {})), patch(
        "services.map_pipeline.fetch_prior_coordinates",
        return_value={},
    ), patch(
        "services.map_pipeline.run_pipeline",
        return_value={
            "translated_results": translated_results,
            "user_ids": [u.id for u in users],
            "raw_coords": np.full((10, 2), np.nan),
        },
    ), patch(
        "services.map_pipeline.write_coordinates"
    ) as write_mock, patch(
        "services.map_pipeline.record_compute_run"
    ) as diagnostics_mock:
        run_pipeline_for_user("u00")

    write_mock.assert_not_called()
    diagnostics_mock.assert_called_once()
    assert diagnostics_mock.call_args.kwargs["published"] is False


def test_successful_validation_publishes_with_consistent_metadata():
    users = [_make_user(f"u{i:02d}") for i in range(10)]
    translated_results = [
        {"user_id": u.id, "x": float(i), "y": float(i + 1), "tier": 1}
        for i, u in enumerate(users)
    ]
    raw_coords = np.array([[float(i), float(i + 1)] for i in range(10)], dtype=float)
    fixed_dt = datetime(2026, 2, 26, 12, 0, 0, tzinfo=timezone.utc)
    fixed_computed_at = fixed_dt.isoformat()
    fixed_version_date = fixed_dt.date().isoformat()

    persisted_rows = [
        {
            "user_id": u.id,
            "x": float(i),
            "y": float(i + 1),
            "computed_at": fixed_computed_at,
            "version_date": fixed_version_date,
        }
        for i, u in enumerate(users)
    ]

    with patch("services.map_pipeline.fetch_all", return_value=(users, {})), patch(
        "services.map_pipeline.fetch_prior_coordinates",
        return_value={},
    ), patch(
        "services.map_pipeline.run_pipeline",
        return_value={
            "translated_results": translated_results,
            "user_ids": [u.id for u in users],
            "raw_coords": raw_coords,
        },
    ), patch(
        "services.map_pipeline.fetch_global_coordinate_rows",
        return_value=persisted_rows,
    ), patch(
        "services.map_pipeline.datetime"
    ) as datetime_mock, patch(
        "services.map_pipeline.write_coordinates"
    ) as write_mock, patch(
        "services.map_pipeline.record_compute_run"
    ) as diagnostics_mock:
        datetime_mock.now.return_value = fixed_dt
        run_pipeline_for_user("u00")

    write_mock.assert_called_once()
    assert write_mock.call_args.kwargs["version_date"] == fixed_version_date
    assert write_mock.call_args.kwargs["computed_at"] == fixed_computed_at
    diagnostics_mock.assert_called_once()
    assert diagnostics_mock.call_args.kwargs["published"] is True
    assert diagnostics_mock.call_args.kwargs["gate_persistence_passed"] is True
