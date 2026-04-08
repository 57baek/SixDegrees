"""Tests for services/map/pipeline.py orchestrator."""
import numpy as np
import pytest
from unittest.mock import patch, MagicMock

from services.map.contracts import PipelineInput, PipelineResult
from models.user import UserProfile


def _make_profile(uid: str) -> UserProfile:
    return UserProfile(id=uid, nickname=f"user_{uid}")


def _make_pipeline_input(interactions: list[dict] | None = None) -> PipelineInput:
    profiles = [_make_profile("uid-1"), _make_profile("uid-2")]
    return PipelineInput(
        profiles=profiles,
        interactions=interactions if interactions is not None else [],
    )


FAKE_COORDS = np.array([[0.1, 0.2], [0.3, 0.4]])


class TestRunHappyPath:
    def test_returns_pipeline_result(self):
        mock_input = _make_pipeline_input()

        with patch("services.map.pipeline.fetch", return_value=mock_input) as mock_fetch, \
             patch("services.map.pipeline.build_combined_distance", return_value=MagicMock()) as mock_dist, \
             patch("services.map.pipeline.project", return_value=FAKE_COORDS) as mock_proj, \
             patch("services.map.pipeline.validate_output") as mock_val, \
             patch("services.map.pipeline.write") as mock_write, \
             patch("services.map.pipeline.record_run") as mock_record:

            from services.map import pipeline
            result = pipeline.run()

        assert isinstance(result, PipelineResult)
        assert result.user_ids == ["uid-1", "uid-2"]
        assert result.edge_count == 0
        assert result.duration_ms >= 0
        np.testing.assert_array_equal(result.coords, FAKE_COORDS)

    def test_record_run_called_with_success(self):
        mock_input = _make_pipeline_input()

        with patch("services.map.pipeline.fetch", return_value=mock_input), \
             patch("services.map.pipeline.build_combined_distance", return_value=MagicMock()), \
             patch("services.map.pipeline.project", return_value=FAKE_COORDS), \
             patch("services.map.pipeline.validate_output"), \
             patch("services.map.pipeline.write"), \
             patch("services.map.pipeline.record_run") as mock_record:

            from services.map import pipeline
            pipeline.run()

        mock_record.assert_called_once()
        call_kwargs = mock_record.call_args.kwargs
        assert call_kwargs["status"] == "success"
        assert call_kwargs["error"] is None

    def test_all_six_steps_called(self):
        mock_input = _make_pipeline_input()
        call_order = []

        with patch("services.map.pipeline.fetch", side_effect=lambda: (call_order.append("fetch"), mock_input)[1]) as mock_fetch, \
             patch("services.map.pipeline.build_combined_distance", side_effect=lambda d: (call_order.append("dist"), MagicMock())[1]) as mock_dist, \
             patch("services.map.pipeline.project", side_effect=lambda m: (call_order.append("proj"), FAKE_COORDS)[1]) as mock_proj, \
             patch("services.map.pipeline.validate_output", side_effect=lambda c, u: call_order.append("val")) as mock_val, \
             patch("services.map.pipeline.write", side_effect=lambda u, c: call_order.append("write")) as mock_write, \
             patch("services.map.pipeline.record_run", side_effect=lambda **kw: call_order.append("record")) as mock_record:

            from services.map import pipeline
            pipeline.run()

        assert call_order == ["fetch", "dist", "proj", "val", "write", "record"]


class TestRunFetchFailure:
    def test_exception_reraised(self):
        with patch("services.map.pipeline.fetch", side_effect=RuntimeError("db error")), \
             patch("services.map.pipeline.record_run"):

            from services.map import pipeline
            with pytest.raises(RuntimeError, match="db error"):
                pipeline.run()

    def test_record_run_called_with_failed(self):
        with patch("services.map.pipeline.fetch", side_effect=RuntimeError("db error")), \
             patch("services.map.pipeline.record_run") as mock_record:

            from services.map import pipeline
            with pytest.raises(RuntimeError):
                pipeline.run()

        mock_record.assert_called_once()
        call_kwargs = mock_record.call_args.kwargs
        assert call_kwargs["status"] == "failed"
        assert call_kwargs["error"] == "db error"

    def test_user_count_zero_when_fetch_fails(self):
        with patch("services.map.pipeline.fetch", side_effect=RuntimeError("db error")), \
             patch("services.map.pipeline.record_run") as mock_record:

            from services.map import pipeline
            with pytest.raises(RuntimeError):
                pipeline.run()

        call_kwargs = mock_record.call_args.kwargs
        assert call_kwargs["user_count"] == 0


class TestRunValidationFailure:
    def test_exception_reraised(self):
        mock_input = _make_pipeline_input()

        with patch("services.map.pipeline.fetch", return_value=mock_input), \
             patch("services.map.pipeline.build_combined_distance", return_value=MagicMock()), \
             patch("services.map.pipeline.project", return_value=FAKE_COORDS), \
             patch("services.map.pipeline.validate_output", side_effect=ValueError("bad coords")), \
             patch("services.map.pipeline.write"), \
             patch("services.map.pipeline.record_run"):

            from services.map import pipeline
            with pytest.raises(ValueError, match="bad coords"):
                pipeline.run()

    def test_record_run_called_with_failed(self):
        mock_input = _make_pipeline_input()

        with patch("services.map.pipeline.fetch", return_value=mock_input), \
             patch("services.map.pipeline.build_combined_distance", return_value=MagicMock()), \
             patch("services.map.pipeline.project", return_value=FAKE_COORDS), \
             patch("services.map.pipeline.validate_output", side_effect=ValueError("bad coords")), \
             patch("services.map.pipeline.write"), \
             patch("services.map.pipeline.record_run") as mock_record:

            from services.map import pipeline
            with pytest.raises(ValueError):
                pipeline.run()

        call_kwargs = mock_record.call_args.kwargs
        assert call_kwargs["status"] == "failed"


class TestEdgeCountCalculation:
    def test_edge_count_counts_nonzero_pairs(self):
        interactions = [
            {"likes_count": 2, "comments_count": 0, "dm_count": 0},   # has likes → count
            {"likes_count": 0, "comments_count": 0, "dm_count": 0},   # all zeros → skip
            {"likes_count": 0, "comments_count": 3, "dm_count": 0},   # has comments → count
        ]
        mock_input = _make_pipeline_input(interactions=interactions)

        with patch("services.map.pipeline.fetch", return_value=mock_input), \
             patch("services.map.pipeline.build_combined_distance", return_value=MagicMock()), \
             patch("services.map.pipeline.project", return_value=FAKE_COORDS), \
             patch("services.map.pipeline.validate_output"), \
             patch("services.map.pipeline.write"), \
             patch("services.map.pipeline.record_run"):

            from services.map import pipeline
            result = pipeline.run()

        assert result.edge_count == 2

    def test_edge_count_in_record_run(self):
        interactions = [
            {"likes_count": 1, "comments_count": 0, "dm_count": 0},
            {"likes_count": 0, "comments_count": 0, "dm_count": 0},
            {"likes_count": 0, "comments_count": 1, "dm_count": 0},
        ]
        mock_input = _make_pipeline_input(interactions=interactions)

        with patch("services.map.pipeline.fetch", return_value=mock_input), \
             patch("services.map.pipeline.build_combined_distance", return_value=MagicMock()), \
             patch("services.map.pipeline.project", return_value=FAKE_COORDS), \
             patch("services.map.pipeline.validate_output"), \
             patch("services.map.pipeline.write"), \
             patch("services.map.pipeline.record_run") as mock_record:

            from services.map import pipeline
            pipeline.run()

        call_kwargs = mock_record.call_args.kwargs
        assert call_kwargs["edge_count"] == 2


def test_run_pipeline_for_user_rejects_empty_string():
    """run_pipeline_for_user raises ValueError for empty user_id."""
    import pytest
    from services.map.pipeline import run_pipeline_for_user
    with pytest.raises(ValueError, match="non-empty string"):
        run_pipeline_for_user("")


def test_run_pipeline_for_user_rejects_non_string():
    """run_pipeline_for_user raises ValueError for non-string user_id."""
    import pytest
    from services.map.pipeline import run_pipeline_for_user
    with pytest.raises(ValueError, match="non-empty string"):
        run_pipeline_for_user(None)
