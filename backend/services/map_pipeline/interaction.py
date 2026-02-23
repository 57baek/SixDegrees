"""Interaction scoring module for the map pipeline.

Converts raw pairwise interaction counts (likes, comments, dms) into a normalized
NxN interaction score matrix in [0, 1].

Normalization strategy (INT-02):
  1. For each interaction type, collect all raw counts across all pairs.
  2. Clip at 95th percentile to prevent superuser collapse.
  3. Min-max normalize to [0, 1].
  4. Final score per pair = weighted sum using INTERACTION_WEIGHTS (INT-01, INT-03).

Adding a new interaction type (INT-01):
  1. Add a column to the `interactions` table in Supabase.
  2. Add an entry to INTERACTION_WEIGHTS in config/algorithm.py.
  Zero logic changes required here.
"""
import numpy as np
from config.algorithm import INTERACTION_WEIGHTS


def compute_interaction_scores(
    user_ids: list[str],
    raw_counts: dict[tuple[str, str], dict[str, int]],
) -> np.ndarray:
    """Compute NxN interaction score matrix from raw pairwise interaction counts.

    Args:
        user_ids: Ordered list of user ID strings. Defines matrix row/column order.
        raw_counts: Dict mapping canonical pair tuples (uid_a, uid_b) where uid_a < uid_b
                    to a dict of interaction type counts, e.g.:
                    {("u1", "u2"): {"likes": 5, "comments": 3, "dms": 1}}
                    Missing keys within a pair dict default to 0.
                    Missing pairs entirely produce interaction_score = 0.0 (INT-04).

    Returns:
        NxN numpy ndarray of interaction scores in [0, 1].
        Symmetric, zeros on diagonal.
        Higher value = more interaction between those users.
    """
    n = len(user_ids)
    id_to_idx: dict[str, int] = {uid: i for i, uid in enumerate(user_ids)}

    # Step 1: Collect all raw values per interaction type (INT-02 normalization prep)
    type_raw_values: dict[str, list[float]] = {t: [] for t in INTERACTION_WEIGHTS}
    pair_keys: list[tuple[str, str]] = list(raw_counts.keys())

    for pair_key in pair_keys:
        pair_data = raw_counts[pair_key]
        for itype in INTERACTION_WEIGHTS:
            type_raw_values[itype].append(float(pair_data.get(itype, 0)))

    # Step 2: Normalize each interaction type independently (INT-02)
    # Clip at 95th percentile, then min-max normalize to [0, 1]
    normalized_per_type: dict[str, dict[tuple[str, str], float]] = {}
    for itype in INTERACTION_WEIGHTS:
        raw_vals = np.array(type_raw_values[itype], dtype=float)
        if len(raw_vals) == 0:
            normalized_per_type[itype] = {}
            continue

        # Use method='lower' to pick an actual observed data value as the clip threshold.
        # This ensures that outliers are clipped to a value that real data points reach,
        # preventing the interpolated-pct approach from inflating the cap near the outlier.
        clip_val = float(np.percentile(raw_vals, 95, method="lower"))
        # Avoid clipping to 0 when all values are 0 (or only one pair exists with val=0)
        if clip_val == 0.0:
            clip_val = float(raw_vals.max()) if raw_vals.max() > 0 else 1.0
        clipped = np.clip(raw_vals, 0.0, clip_val)

        # Normalize from 0 → clip_val so that 0 interactions always scores 0.0
        # and max (clipped) interactions score 1.0. Using clip_val as denominator
        # means normalization range is anchored at 0 regardless of actual minimum.
        norm_vals = clipped / clip_val

        normalized_per_type[itype] = dict(zip(pair_keys, norm_vals.tolist()))

    # Step 3: Build NxN matrix using weighted sum of normalized scores (INT-03)
    matrix = np.zeros((n, n), dtype=float)
    for pair_key in pair_keys:
        uid_a, uid_b = pair_key
        if uid_a not in id_to_idx or uid_b not in id_to_idx:
            continue  # skip pairs for users not in this user set
        i = id_to_idx[uid_a]
        j = id_to_idx[uid_b]

        # INT-01: weight dispatch purely from INTERACTION_WEIGHTS dict
        score = sum(
            INTERACTION_WEIGHTS[itype] * normalized_per_type[itype].get(pair_key, 0.0)
            for itype in INTERACTION_WEIGHTS
        )
        matrix[i][j] = score
        matrix[j][i] = score  # symmetric (INT-03, DIST-04 via caller)

    # Diagonal stays 0.0 (no self-interaction)
    np.fill_diagonal(matrix, 0.0)
    return matrix
