import numpy as np

from services.map_pipeline.contracts import StabilityInput
from services.map_pipeline.stability import stabilize_coordinates


def test_stability_clips_movement_to_max_delta():
    user_ids = ["u1", "u2", "u3"]
    candidate_coordinates = np.array(
        [
            [4.0, 0.0],
            [0.2, 0.1],
            [0.0, 0.0],
        ],
        dtype=float,
    )
    prior_coordinates = {
        "u1": (0.0, 0.0),
    }

    result = stabilize_coordinates(
        StabilityInput(
            user_ids=user_ids,
            candidate_coordinates=candidate_coordinates,
            prior_coordinates=prior_coordinates,
            max_delta=1.0,
        )
    )

    u1_idx = user_ids.index("u1")
    moved = float(np.linalg.norm(result.coordinates[u1_idx] - np.array([0.0, 0.0])))

    assert moved <= 1.0 + 1e-9
    assert result.metrics["max_delta"] <= 1.0 + 1e-9
    assert result.metrics["moved_count"] == 1
