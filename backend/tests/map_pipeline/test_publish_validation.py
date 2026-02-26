import numpy as np
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
