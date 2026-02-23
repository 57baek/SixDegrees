"""Map pipeline orchestrator.

Connects all four algorithm stages into a single end-to-end computation:
  1. interaction.py    — raw interaction counts → NxN interaction score matrix
  2. scoring.py        — UserProfiles + interaction matrix → NxN combined distance matrix
  3. tsne_projector.py — combined distance matrix → (N, 2) raw 2D coordinates
  4. origin_translator.py — raw coords + requesting user → translated coords with tiers

Phase 2 contract: This function is PURE COMPUTATION — no Supabase reads or writes.
Phase 3 will wrap this with data_fetcher (reads) and coord_writer (writes).

Data model note:
    Accepts list[UserProfile] with .city/.state fields (existing model).
    Phase 3's data_fetcher.py maps location_city→city and location_state→state
    when constructing UserProfile objects from DB rows.
"""
import numpy as np
from models.user import UserProfile
from services.map_pipeline.interaction import compute_interaction_scores
from services.map_pipeline.scoring import build_combined_distance_matrix
from services.map_pipeline.tsne_projector import project_tsne
from services.map_pipeline.origin_translator import translate_and_assign_tiers


def run_pipeline(
    users: list[UserProfile],
    raw_interaction_counts: dict[tuple[str, str], dict[str, int]],
    requesting_user_id: str,
) -> dict:
    """Run the full map pipeline for a single requesting user.

    Args:
        users: All UserProfile objects to include in the map. Must have N >= 10.
               Uses existing UserProfile model (.city/.state fields).
        raw_interaction_counts: Dict mapping canonical pair tuples (uid_a, uid_b)
                                where uid_a < uid_b to interaction type counts:
                                {("u1", "u2"): {"likes": 5, "comments": 3, "dms": 1}}
                                Missing pairs default to 0.0 interaction score.
        requesting_user_id: The user who should be at (0.0, 0.0) in the output.
                           Must be present in the users list.

    Returns:
        {
            "raw_coords": np.ndarray,           # (N, 2) before translation — TSNE-04
            "translated_results": list[dict],   # [{"user_id": str, "x": float, "y": float, "tier": int}]
            "user_ids": list[str],              # ordered user ID list (matches raw_coords rows)
        }

    Raises:
        ValueError: If N < 10 (propagated from tsne_projector).
        ValueError: If requesting_user_id not in users.
    """
    # Validate requesting user is present
    user_id_set = {u.id for u in users}
    if requesting_user_id not in user_id_set:
        raise ValueError(
            f"requesting_user_id '{requesting_user_id}' not found in users list."
        )

    # Ordered user IDs — consistent index mapping across all stages
    user_ids = [u.id for u in users]

    # Stage 1: Interaction scoring → NxN interaction matrix in [0, 1]
    interaction_matrix = compute_interaction_scores(user_ids, raw_interaction_counts)

    # Stage 2: Combined distance matrix → NxN in [0, 1]
    combined_dist_matrix = build_combined_distance_matrix(users, interaction_matrix)

    # Stage 3: t-SNE projection → (N, 2) raw coordinates (raises ValueError if N < 10)
    raw_coords = project_tsne(combined_dist_matrix)  # TSNE-04: raw, before translation

    # Stage 4: Translate to origin + assign tiers
    translated_results = translate_and_assign_tiers(
        user_ids, raw_coords, requesting_user_id
    )

    return {
        "raw_coords": raw_coords,             # TSNE-04: preserved for Procrustes alignment
        "translated_results": translated_results,
        "user_ids": user_ids,
    }
