"""Validation gates for fail-closed map coordinate publishing."""

from dataclasses import dataclass
from typing import Any

import numpy as np


MIN_PROFILE_COUNT = 10
MIN_COORDINATE_SPREAD = 1e-6


@dataclass(frozen=True)
class PublishValidationResult:
    """Structured validation outcome used by orchestration and diagnostics."""

    gate_input_passed: bool
    gate_embedding_passed: bool
    gate_persistence_passed: bool
    publish_allowed: bool
    publish_block_reason: str | None
    quality_metrics: dict[str, Any]
    gate_details: dict[str, Any]


def validate_candidate_publish(
    *,
    translated_results: list[dict[str, Any]],
    user_ids: list[str],
    raw_coords: np.ndarray,
    prior_coordinates: dict[str, tuple[float, float]] | None = None,
    persisted_rows: list[dict[str, Any]] | None = None,
    expected_version_date: str | None = None,
    expected_computed_at: str | None = None,
    check_persistence: bool = False,
) -> PublishValidationResult:
    """Validate candidate coordinates before/after publish.

    When ``check_persistence`` is False, this runs input + embedding gates.
    When ``check_persistence`` is True, it additionally requires persisted-row
    count and metadata consistency.
    """

    candidate_user_ids = [str(row.get("user_id")) for row in translated_results]
    candidate_id_set = set(candidate_user_ids)

    gate_input_passed = (
        len(user_ids) >= MIN_PROFILE_COUNT
        and len(translated_results) == len(user_ids)
        and len(candidate_id_set) == len(user_ids)
        and candidate_id_set == set(user_ids)
        and _all_candidate_coordinates_finite(translated_results)
    )

    gate_embedding_passed = _embedding_gate(raw_coords)

    gate_persistence_passed = True
    persistence_details: dict[str, Any] = {}
    if check_persistence:
        gate_persistence_passed, persistence_details = _persistence_gate(
            persisted_rows or [],
            expected_user_ids=set(user_ids),
            expected_version_date=expected_version_date,
            expected_computed_at=expected_computed_at,
        )

    publish_allowed = gate_input_passed and gate_embedding_passed and gate_persistence_passed

    block_reason = None
    if not gate_input_passed:
        block_reason = "input_gate_failed"
    elif not gate_embedding_passed:
        block_reason = "embedding_gate_failed"
    elif not gate_persistence_passed:
        block_reason = "persistence_gate_failed"

    quality_metrics = _build_quality_metrics(
        raw_coords=raw_coords,
        translated_results=translated_results,
        prior_coordinates=prior_coordinates,
    )

    gate_details: dict[str, Any] = {
        "candidate_user_count": len(candidate_id_set),
        "expected_user_count": len(user_ids),
        "has_unique_candidate_ids": len(candidate_id_set) == len(candidate_user_ids),
    }
    gate_details.update(persistence_details)

    return PublishValidationResult(
        gate_input_passed=gate_input_passed,
        gate_embedding_passed=gate_embedding_passed,
        gate_persistence_passed=gate_persistence_passed,
        publish_allowed=publish_allowed,
        publish_block_reason=block_reason,
        quality_metrics=quality_metrics,
        gate_details=gate_details,
    )


def _all_candidate_coordinates_finite(translated_results: list[dict[str, Any]]) -> bool:
    for row in translated_results:
        x = row.get("x")
        y = row.get("y")
        if x is None or y is None:
            return False
        if not np.isfinite(float(x)) or not np.isfinite(float(y)):
            return False
    return True


def _embedding_gate(raw_coords: np.ndarray) -> bool:
    if raw_coords.ndim != 2 or raw_coords.shape[1] != 2:
        return False
    if raw_coords.shape[0] < MIN_PROFILE_COUNT:
        return False
    if not np.isfinite(raw_coords).all():
        return False

    spread_x = float(np.ptp(raw_coords[:, 0]))
    spread_y = float(np.ptp(raw_coords[:, 1]))
    return spread_x > MIN_COORDINATE_SPREAD or spread_y > MIN_COORDINATE_SPREAD


def _persistence_gate(
    persisted_rows: list[dict[str, Any]],
    *,
    expected_user_ids: set[str],
    expected_version_date: str | None,
    expected_computed_at: str | None,
) -> tuple[bool, dict[str, Any]]:
    persisted_ids = {str(row.get("user_id")) for row in persisted_rows}
    metadata_ok = True
    for row in persisted_rows:
        if expected_version_date is not None and str(row.get("version_date")) != expected_version_date:
            metadata_ok = False
            break
        if expected_computed_at is not None and str(row.get("computed_at")) != expected_computed_at:
            metadata_ok = False
            break

    passed = (
        len(persisted_rows) == len(expected_user_ids)
        and persisted_ids == expected_user_ids
        and metadata_ok
    )

    return passed, {
        "persisted_user_count": len(persisted_ids),
        "persisted_row_count": len(persisted_rows),
        "persistence_metadata_ok": metadata_ok,
    }


def _build_quality_metrics(
    *,
    raw_coords: np.ndarray,
    translated_results: list[dict[str, Any]],
    prior_coordinates: dict[str, tuple[float, float]] | None,
) -> dict[str, Any]:
    metrics: dict[str, Any] = {
        "spread_x": float(np.ptp(raw_coords[:, 0])) if raw_coords.size else 0.0,
        "spread_y": float(np.ptp(raw_coords[:, 1])) if raw_coords.size else 0.0,
        "candidate_row_count": len(translated_results),
    }

    if not prior_coordinates:
        metrics.update(
            {
                "moved_count": 0,
                "mean_delta": 0.0,
                "p95_delta": 0.0,
                "max_delta": 0.0,
            }
        )
        return metrics

    deltas: list[float] = []
    for row in translated_results:
        uid = str(row.get("user_id"))
        if uid not in prior_coordinates:
            continue
        prev_x, prev_y = prior_coordinates[uid]
        dx = float(row["x"]) - float(prev_x)
        dy = float(row["y"]) - float(prev_y)
        deltas.append(float(np.hypot(dx, dy)))

    if not deltas:
        metrics.update(
            {
                "moved_count": 0,
                "mean_delta": 0.0,
                "p95_delta": 0.0,
                "max_delta": 0.0,
            }
        )
        return metrics

    deltas_arr = np.asarray(deltas, dtype=float)
    metrics.update(
        {
            "moved_count": int((deltas_arr > 0).sum()),
            "mean_delta": float(deltas_arr.mean()),
            "p95_delta": float(np.percentile(deltas_arr, 95)),
            "max_delta": float(deltas_arr.max()),
        }
    )
    return metrics
