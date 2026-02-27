"""Sparse interaction refinement stage with recency weighting."""

from __future__ import annotations

import math

import numpy as np

from models.config.algorithm import (
    INTERACTION_SENSITIVITY_BASELINE,
    INTERACTION_WEIGHTS,
)
from services.map_pipeline.contracts import (
    InteractionSensitivity,
    RefinementInput,
    RefinementResult,
    SparseEdge,
)

_RECENCY_KEYS = (
    "days_since_last_interaction",
    "last_interaction_days",
    "recency_days",
)
_RECENCY_DECAY_DAYS = 30.0


def refine_sparse_embedding(input_data: RefinementInput) -> RefinementResult:
    """Refine profile coordinates using sparse interaction pulls."""
    coordinates = input_data.base_coordinates.astype(float, copy=True)
    interaction_sensitivity = _resolve_interaction_sensitivity(input_data)
    interaction_edges = _build_interaction_edges(
        input_data.user_ids,
        input_data.raw_interaction_counts,
        interaction_sensitivity,
    )

    if not interaction_edges:
        return RefinementResult(
            user_ids=input_data.user_ids,
            coordinates=coordinates,
            interaction_edges=[],
        )

    id_to_index = {user_id: index for index, user_id in enumerate(input_data.user_ids)}
    for _ in range(input_data.iterations):
        delta = np.zeros_like(coordinates)
        for edge in interaction_edges:
            i = id_to_index[edge.user_id_a]
            j = id_to_index[edge.user_id_b]
            pull = input_data.step_size * edge.final_weight
            vec = coordinates[j] - coordinates[i]
            delta[i] += pull * vec
            delta[j] -= pull * vec
        coordinates = coordinates + delta
        coordinates = coordinates - coordinates.mean(axis=0, keepdims=True)

    return RefinementResult(
        user_ids=input_data.user_ids,
        coordinates=coordinates,
        interaction_edges=interaction_edges,
    )


def _build_interaction_edges(
    user_ids: list[str],
    raw_interaction_counts: dict[tuple[str, str], dict[str, int | float]],
    interaction_sensitivity: InteractionSensitivity,
) -> list[SparseEdge]:
    user_set = set(user_ids)
    edges: list[SparseEdge] = []

    for (uid_a, uid_b), counts in raw_interaction_counts.items():
        if uid_a not in user_set or uid_b not in user_set:
            continue

        interaction_weight, weighted_interactions, sensitivity_multiplier = (
            _interaction_weight(counts, interaction_sensitivity)
        )
        if interaction_weight <= 0.0:
            continue

        recency_weight = _recency_weight(counts)
        final_weight = float(np.clip(interaction_weight * recency_weight, 0.0, 1.0))

        if final_weight <= 0.0:
            continue

        user_id_a, user_id_b = _canonical_pair(uid_a, uid_b)
        edges.append(
            SparseEdge(
                user_id_a=user_id_a,
                user_id_b=user_id_b,
                interaction_weight=interaction_weight,
                recency_weight=recency_weight,
                final_weight=final_weight,
                weighted_interactions=weighted_interactions,
                sensitivity_multiplier=sensitivity_multiplier,
            )
        )

    return edges


def _interaction_weight(
    counts: dict[str, int | float],
    interaction_sensitivity: InteractionSensitivity,
) -> tuple[float, float, float]:
    weighted_sum = 0.0
    for interaction_name, interaction_weight in INTERACTION_WEIGHTS.items():
        weighted_sum += interaction_weight * float(counts.get(interaction_name, 0.0))
    if weighted_sum <= 0.0:
        return (0.0, 0.0, 0.0)

    normalizer = max(interaction_sensitivity.normalizer, 1e-6)
    normalized_signal = weighted_sum / normalizer
    sensitivity_multiplier = interaction_sensitivity.strength_scale * math.pow(
        1.0 + normalized_signal,
        interaction_sensitivity.curve_exponent,
    )
    interaction_weight = 1.0 - math.exp(-normalized_signal * sensitivity_multiplier)
    interaction_weight = float(
        np.clip(interaction_weight, 0.0, interaction_sensitivity.max_weight)
    )
    return (interaction_weight, weighted_sum, float(sensitivity_multiplier))


def _resolve_interaction_sensitivity(
    input_data: RefinementInput,
) -> InteractionSensitivity:
    if input_data.interaction_sensitivity is not None:
        return input_data.interaction_sensitivity
    return InteractionSensitivity(
        strength_scale=float(INTERACTION_SENSITIVITY_BASELINE["strength_scale"]),
        curve_exponent=float(INTERACTION_SENSITIVITY_BASELINE["curve_exponent"]),
        normalizer=float(INTERACTION_SENSITIVITY_BASELINE["normalizer"]),
        max_weight=float(INTERACTION_SENSITIVITY_BASELINE["max_weight"]),
    )


def _recency_weight(counts: dict[str, int | float]) -> float:
    days = None
    for key in _RECENCY_KEYS:
        if key in counts:
            days = float(counts[key])
            break

    if days is None:
        return 1.0
    if days <= 0:
        return 1.0
    return float(math.exp(-days / _RECENCY_DECAY_DAYS))


def _canonical_pair(uid_a: str, uid_b: str) -> tuple[str, str]:
    return (uid_a, uid_b) if uid_a < uid_b else (uid_b, uid_a)
