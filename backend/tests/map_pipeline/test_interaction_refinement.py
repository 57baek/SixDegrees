import numpy as np

from services.map_pipeline.contracts import RefinementInput, SparseEdge
from services.map_pipeline.interaction_refinement import refine_sparse_embedding


def _distance(coords: np.ndarray, user_ids: list[str], uid_a: str, uid_b: str) -> float:
    idx_a = user_ids.index(uid_a)
    idx_b = user_ids.index(uid_b)
    return float(np.linalg.norm(coords[idx_a] - coords[idx_b]))


def test_refinement_applies_recency_weighted_interaction_pulls():
    user_ids = ["u1", "u2", "u3", "u4"]
    base_coordinates = np.array(
        [
            [0.0, 0.0],
            [2.0, 0.0],
            [0.0, 2.0],
            [2.0, 2.0],
        ],
        dtype=float,
    )
    profile_edges = [
        SparseEdge("u1", "u3", 0.25, 1.0, 0.25),
        SparseEdge("u2", "u4", 0.25, 1.0, 0.25),
    ]

    raw_counts = {
        ("u1", "u2"): {
            "likes": 80,
            "comments": 40,
            "dms": 20,
            "days_since_last_interaction": 1,
        },
        ("u3", "u4"): {
            "likes": 80,
            "comments": 40,
            "dms": 20,
            "days_since_last_interaction": 120,
        },
    }

    refined = refine_sparse_embedding(
        RefinementInput(
            user_ids=user_ids,
            base_coordinates=base_coordinates,
            profile_edges=profile_edges,
            raw_interaction_counts=raw_counts,
            step_size=0.08,
            iterations=20,
        )
    )

    baseline_u1_u2 = _distance(base_coordinates, user_ids, "u1", "u2")
    baseline_u3_u4 = _distance(base_coordinates, user_ids, "u3", "u4")
    refined_u1_u2 = _distance(refined.coordinates, user_ids, "u1", "u2")
    refined_u3_u4 = _distance(refined.coordinates, user_ids, "u3", "u4")

    assert refined_u1_u2 < baseline_u1_u2
    assert refined_u1_u2 < refined_u3_u4
    assert refined_u3_u4 <= baseline_u3_u4
