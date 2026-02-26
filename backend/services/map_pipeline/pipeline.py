"""Map pipeline orchestrator using sparse compute stages."""

import numpy as np

from models.user import UserProfile
from services.map_pipeline.contracts import (
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
) -> dict:
    """Run sparse embedding, interaction refinement, and stability stages."""
    user_id_set = {u.id for u in users}
    if requesting_user_id not in user_id_set:
        raise ValueError(
            f"requesting_user_id '{requesting_user_id}' not found in users list."
        )

    embedding_result = build_sparse_profile_embedding(
        SparseEmbeddingInput(users=users)
    )

    refinement_result = refine_sparse_embedding(
        RefinementInput(
            user_ids=embedding_result.user_ids,
            base_coordinates=embedding_result.coordinates,
            profile_edges=embedding_result.profile_edges,
            raw_interaction_counts=raw_interaction_counts,
        )
    )

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
    }
