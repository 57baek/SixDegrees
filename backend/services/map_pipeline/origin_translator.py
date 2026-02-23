"""Origin translation and tier assignment for the map pipeline.

After t-SNE projection, this module:
  1. Shifts all coordinates so the requesting user is at (0.0, 0.0) — ORIG-01
  2. Assigns tier labels based on 2D Euclidean distance from origin — ORIG-02
  3. Includes the requesting user themselves in the output at (0,0) as Tier 1 — ORIG-02
  4. Is a stateless pure function — call independently per requesting user — ORIG-03

Tier assignment uses 2D Euclidean distances from the translated coordinates:
  Tier 1: 5 nearest users (closest circle — first degree connections)
  Tier 2: next 10 users (second degree, ranks 6-15)
  Tier 3: all remaining users within 0.75 Euclidean distance threshold

NOTE: Tier 3 is a label, not a filter. All users appear in the output regardless
of distance. The _MAX_DIST constant is retained for reference and future use
(e.g., coord_writer.py may choose to exclude users beyond this threshold).
"""
import numpy as np

# KNN tier thresholds — mirror clustering.py constants for consistency
_K1 = 5          # Tier 1: 5 nearest non-requesting users
_K2 = 15         # Tier 2: up to rank 15 (so Tier 2 = ranks 6-15)
_MAX_DIST = 0.75  # Tier 3 cutoff reference — users beyond this would be outer ring


def translate_and_assign_tiers(
    user_ids: list[str],
    raw_coords: np.ndarray,
    requesting_user_id: str,
) -> list[dict]:
    """Translate coordinates to origin and assign tier labels.

    Args:
        user_ids: Ordered list of user IDs (same order as raw_coords rows).
        raw_coords: (N, 2) ndarray of raw t-SNE coordinates (NOT yet translated).
                    This is the direct output of project_tsne().
        requesting_user_id: The user who should be placed at (0.0, 0.0).

    Returns:
        List of dicts, one per user (including the requesting user themselves):
        [{"user_id": str, "x": float, "y": float, "tier": int}, ...]
        The requesting user is always at x=0.0, y=0.0 with tier=1.

    Raises:
        ValueError: If requesting_user_id is not in user_ids.
    """
    if requesting_user_id not in user_ids:
        raise ValueError(
            f"requesting_user_id '{requesting_user_id}' not found in user_ids list."
        )

    id_to_idx = {uid: i for i, uid in enumerate(user_ids)}
    req_idx = id_to_idx[requesting_user_id]

    # ORIG-01: translate so requesting user is at (0.0, 0.0)
    translated = raw_coords - raw_coords[req_idx]  # broadcast subtraction

    # Compute 2D Euclidean distances from origin for all users
    distances = np.sqrt(translated[:, 0] ** 2 + translated[:, 1] ** 2)

    # Sort all OTHER users by distance (ascending)
    other_indices = [i for i in range(len(user_ids)) if i != req_idx]
    other_indices_sorted = sorted(other_indices, key=lambda i: distances[i])

    results: list[dict] = []

    # ORIG-02: requesting user at (0,0) is always Tier 1
    results.append({
        "user_id": requesting_user_id,
        "x": 0.0,
        "y": 0.0,
        "tier": 1,
    })

    # Assign tiers to all other users
    for rank, other_idx in enumerate(other_indices_sorted, start=1):
        if rank <= _K1:
            tier = 1
        elif rank <= _K2:
            tier = 2
        else:
            tier = 3

        results.append({
            "user_id": user_ids[other_idx],
            "x": float(translated[other_idx, 0]),
            "y": float(translated[other_idx, 1]),
            "tier": tier,
        })

    return results
