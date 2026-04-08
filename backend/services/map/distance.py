import numpy as np

from config.settings import ALPHA, BETA, INTERACTION_WEIGHTS
from services.map.contracts import PipelineInput
from services.matching.scoring import build_similarity_matrix, apply_weights, similarity_to_distance


def build_combined_distance(data: PipelineInput) -> np.ndarray:
    """Build a combined N×N distance matrix from profile similarity and interaction data.

    Algorithm:
      1. Profile distance: build_similarity_matrix → apply_weights → similarity_to_distance
      2. Interaction distance: normalize raw interaction scores then invert
      3. Combined: ALPHA * profile_dist + BETA * interaction_dist, clipped to [0, 1]

    Returns:
        np.ndarray: shape (N, N), symmetric, diagonal = 0, values in [0, 1]
    """
    profiles = data.profiles
    n = len(profiles)

    # --- 1. Profile distance ---
    sim_matrix = build_similarity_matrix(profiles)
    weighted = apply_weights(sim_matrix)
    profile_dist = similarity_to_distance(weighted)  # (N, N), diag=0

    # --- 2. Interaction distance ---
    # Build canonical-pair lookup: (uid_a, uid_b) where uid_a < uid_b
    interaction_map: dict[tuple[str, str], dict] = {
        (r["user_id_a"], r["user_id_b"]): r for r in data.interactions
    }

    uid_to_idx: dict[str, int] = {p.id: i for i, p in enumerate(profiles)}

    # Compute raw interaction scores for every pair
    raw_scores = np.zeros((n, n))
    for i in range(n):
        for j in range(i + 1, n):
            uid_i = profiles[i].id
            uid_j = profiles[j].id
            key = (min(uid_i, uid_j), max(uid_i, uid_j))
            row = interaction_map.get(key)
            if row is not None:
                score = (
                    row.get("likes_count", 0) * INTERACTION_WEIGHTS["likes_count"]
                    + row.get("comments_count", 0) * INTERACTION_WEIGHTS["comments_count"]
                    + row.get("dm_count", 0) * INTERACTION_WEIGHTS["dm_count"]
                )
                raw_scores[i][j] = score
                raw_scores[j][i] = score

    # Normalize to [0, 1]
    max_score = raw_scores.max()
    if max_score > 0:
        normalized = raw_scores / max_score
    else:
        normalized = raw_scores  # all zeros

    # More interaction → lower distance
    interaction_dist = 1.0 - normalized
    np.fill_diagonal(interaction_dist, 0.0)

    # --- 3. Combine ---
    combined = ALPHA * profile_dist + BETA * interaction_dist
    combined = np.clip(combined, 0.0, 1.0)
    np.fill_diagonal(combined, 0.0)

    return combined
