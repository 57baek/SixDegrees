"""Map pipeline orchestrator using sparse compute stages."""

import numpy as np

from models.config.algorithm import INTERACTION_SENSITIVITY_MODES
from models.user import UserProfile
from services.map_pipeline.contracts import (
    InteractionSensitivity,
    RawInteractionCounts,
    RefinementInput,
    SparseEmbeddingInput,
    StabilityInput,
)
from services.map_pipeline.interaction_refinement import refine_sparse_embedding
from services.map_pipeline.origin_translator import translate_and_assign_tiers
from services.map_pipeline.sparse_embedding import build_sparse_profile_embedding
from services.map_pipeline.stability import stabilize_coordinates


def run_pipeline(
    users: list[UserProfile],
    raw_interaction_counts: RawInteractionCounts,
    requesting_user_id: str,
    prior_coordinates: dict[str, tuple[float, float]] | None = None,
    max_movement_delta: float = 0.35,
    interaction_sensitivity: InteractionSensitivity | None = None,
) -> dict:
    """Run sparse embedding, interaction refinement, and stability stages."""
    user_id_set = {u.id for u in users}
    if requesting_user_id not in user_id_set:
        raise ValueError(
            f"requesting_user_id '{requesting_user_id}' not found in users list."
        )

    resolved_sensitivity = _resolve_interaction_sensitivity(interaction_sensitivity)

    embedding_result = build_sparse_profile_embedding(
        SparseEmbeddingInput(users=users)
    )

    refinement_input = RefinementInput(
        user_ids=embedding_result.user_ids,
        base_coordinates=embedding_result.coordinates,
        profile_edges=embedding_result.profile_edges,
        raw_interaction_counts=raw_interaction_counts,
        interaction_sensitivity=resolved_sensitivity,
    )
    refinement_result = refine_sparse_embedding(refinement_input)

    stability_result = stabilize_coordinates(
        StabilityInput(
            user_ids=refinement_result.user_ids,
            candidate_coordinates=refinement_result.coordinates,
            prior_coordinates=prior_coordinates,
            max_delta=max_movement_delta,
        )
    )

    translated_results = translate_and_assign_tiers(
        stability_result.user_ids,
        stability_result.coordinates,
        requesting_user_id,
    )

    return {
        "raw_coords": stability_result.coordinates,
        "translated_results": translated_results,
        "user_ids": stability_result.user_ids,
        "diagnostics": {
            "refinement": {
                "step_size": float(refinement_input.step_size),
                "iterations": int(refinement_input.iterations),
                "interaction_sensitivity": {
                    "mode": resolved_sensitivity.mode,
                    "strength_scale": float(resolved_sensitivity.strength_scale or 0.0),
                    "curve_exponent": float(resolved_sensitivity.curve_exponent or 0.0),
                    "normalizer": float(resolved_sensitivity.normalizer or 0.0),
                    "max_weight": float(resolved_sensitivity.max_weight or 0.0),
                },
            },
            "interaction_edges": _serialize_interaction_edges(
                refinement_result.interaction_edges
            ),
        },
    }


def _resolve_interaction_sensitivity(
    interaction_sensitivity: InteractionSensitivity | None,
) -> InteractionSensitivity:
    sensitivity = interaction_sensitivity or InteractionSensitivity()
    preset = INTERACTION_SENSITIVITY_MODES[sensitivity.mode]
    return InteractionSensitivity(
        mode=sensitivity.mode,
        strength_scale=float(
            sensitivity.strength_scale
            if sensitivity.strength_scale is not None
            else preset["strength_scale"]
        ),
        curve_exponent=float(
            sensitivity.curve_exponent
            if sensitivity.curve_exponent is not None
            else preset["curve_exponent"]
        ),
        normalizer=float(
            sensitivity.normalizer
            if sensitivity.normalizer is not None
            else preset["normalizer"]
        ),
        max_weight=float(
            sensitivity.max_weight
            if sensitivity.max_weight is not None
            else preset["max_weight"]
        ),
    )


def _serialize_interaction_edges(edges: list) -> list[dict[str, float | str]]:
    return [
        {
            "user_id_a": edge.user_id_a,
            "user_id_b": edge.user_id_b,
            "interaction_weight": float(edge.interaction_weight),
            "recency_weight": float(edge.recency_weight),
            "final_weight": float(edge.final_weight),
            "weighted_interactions": float(edge.weighted_interactions),
            "sensitivity_multiplier": float(edge.sensitivity_multiplier),
        }
        for edge in sorted(edges, key=lambda item: (item.user_id_a, item.user_id_b))
    ]
