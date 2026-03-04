"""Coordinate stability stage with alignment and movement clipping."""

from __future__ import annotations

import numpy as np

from services.map_pipeline.contracts import StabilityInput, StabilityMetrics, StabilityResult


def stabilize_coordinates(input_data: StabilityInput) -> StabilityResult:
    """Align to prior anchors and clip per-user movement."""
    aligned = _align_to_prior(
        input_data.user_ids,
        input_data.candidate_coordinates,
        input_data.prior_coordinates,
    )
    clipped, deltas = _clip_movement(
        input_data.user_ids,
        aligned,
        input_data.prior_coordinates,
        input_data.max_delta,
    )
    metrics = _build_metrics(deltas)

    return StabilityResult(
        user_ids=input_data.user_ids,
        coordinates=clipped,
        metrics=metrics,
    )


def _align_to_prior(
    user_ids: list[str],
    candidate_coordinates: np.ndarray,
    prior_coordinates: dict[str, tuple[float, float]] | None,
) -> np.ndarray:
    coordinates = candidate_coordinates.astype(float, copy=True)
    if not prior_coordinates:
        return coordinates

    anchor_indices: list[int] = []
    candidate_anchors: list[list[float]] = []
    prior_anchors: list[list[float]] = []

    for index, user_id in enumerate(user_ids):
        prior = prior_coordinates.get(user_id)
        if prior is None:
            continue
        anchor_indices.append(index)
        candidate_anchors.append([coordinates[index, 0], coordinates[index, 1]])
        prior_anchors.append([prior[0], prior[1]])

    if len(anchor_indices) < 2:
        return coordinates

    x = np.array(candidate_anchors, dtype=float)
    y = np.array(prior_anchors, dtype=float)
    x_centroid = x.mean(axis=0)
    y_centroid = y.mean(axis=0)
    x_centered = x - x_centroid
    y_centered = y - y_centroid

    covariance = x_centered.T @ y_centered
    u, _, vt = np.linalg.svd(covariance)
    rotation = u @ vt

    if np.linalg.det(rotation) < 0:
        vt[-1, :] *= -1
        rotation = u @ vt

    return (coordinates - x_centroid) @ rotation + y_centroid


def _clip_movement(
    user_ids: list[str],
    coordinates: np.ndarray,
    prior_coordinates: dict[str, tuple[float, float]] | None,
    max_delta: float,
) -> tuple[np.ndarray, list[float]]:
    clipped = coordinates.astype(float, copy=True)
    if not prior_coordinates:
        return clipped, []

    deltas: list[float] = []
    for index, user_id in enumerate(user_ids):
        prior = prior_coordinates.get(user_id)
        if prior is None:
            continue

        prior_vec = np.array(prior, dtype=float)
        delta_vec = clipped[index] - prior_vec
        delta_norm = float(np.linalg.norm(delta_vec))

        if max_delta > 0 and delta_norm > max_delta:
            clipped[index] = prior_vec + (delta_vec / delta_norm) * max_delta
            delta_norm = max_delta

        deltas.append(delta_norm)

    return clipped, deltas


def _build_metrics(deltas: list[float]) -> StabilityMetrics:
    if not deltas:
        return {
            "moved_count": 0,
            "mean_delta": 0.0,
            "p95_delta": 0.0,
            "max_delta": 0.0,
        }

    delta_array = np.array(deltas, dtype=float)
    return {
        "moved_count": int(np.count_nonzero(delta_array > 0.0)),
        "mean_delta": float(delta_array.mean()),
        "p95_delta": float(np.percentile(delta_array, 95)),
        "max_delta": float(delta_array.max()),
    }
