import numpy as np

from models.user import UserProfile
from scripts.run_phase24_demo_pipeline import _build_distance_curve_rows
from services.map_pipeline.contracts import (
    InteractionSensitivity,
    InteractionSensitivityMode,
    RefinementInput,
    SparseEmbeddingResult,
)
from services.map_pipeline.interaction_refinement import refine_sparse_embedding
from services.map_pipeline.pipeline import run_pipeline


def _distance(coords: np.ndarray, user_ids: list[str], uid_a: str, uid_b: str) -> float:
    idx_a = user_ids.index(uid_a)
    idx_b = user_ids.index(uid_b)
    return float(np.linalg.norm(coords[idx_a] - coords[idx_b]))


def _make_user(uid: str, interests: list[str], age: int) -> UserProfile:
    return UserProfile(
        id=uid,
        nickname=uid,
        interests=interests,
        languages=["English"],
        city="London",
        state="LN",
        education="Computer Science",
        occupation="Engineer",
        industry="Technology",
        age=age,
        timezone="UTC",
    )


def _refinement_input(amplification: int) -> RefinementInput:
    user_ids = ["Eleanor", "Winston", "u3", "u4"]
    base_coordinates = np.array(
        [
            [0.0, 0.0],
            [2.0, 0.0],
            [0.0, 2.0],
            [2.0, 2.0],
        ],
        dtype=float,
    )
    return RefinementInput(
        user_ids=user_ids,
        base_coordinates=base_coordinates,
        profile_edges=[],
        raw_interaction_counts={
            ("Eleanor", "Winston"): {
                "likes": 3 * amplification,
                "comments": 2 * amplification,
                "dms": 1 * amplification,
                "days_since_last_interaction": 1,
            },
            ("u3", "u4"): {
                "likes": 3,
                "comments": 2,
                "dms": 1,
                "days_since_last_interaction": 1,
            },
        },
        step_size=0.08,
        iterations=24,
        interaction_sensitivity=InteractionSensitivity(
            strength_scale=1.8,
            curve_exponent=0.82,
            normalizer=7.0,
            max_weight=0.97,
        ),
    )


def test_eleanor_winston_distance_improves_with_amplification():
    amplification_levels = [1, 2, 4, 8]
    distances: list[float] = []
    edge_weights: list[float] = []

    for amplification in amplification_levels:
        refined = refine_sparse_embedding(_refinement_input(amplification))
        distances.append(
            _distance(refined.coordinates, refined.user_ids, "Eleanor", "Winston")
        )
        eleanor_edge = next(
            edge
            for edge in refined.interaction_edges
            if {edge.user_id_a, edge.user_id_b} == {"Eleanor", "Winston"}
        )
        edge_weights.append(eleanor_edge.final_weight)

    assert all(curr <= prev + 1e-6 for prev, curr in zip(distances, distances[1:]))
    assert all(curr >= prev for prev, curr in zip(edge_weights, edge_weights[1:]))


def test_amplification_creates_stronger_pull_than_baseline():
    baseline = refine_sparse_embedding(_refinement_input(amplification=1))
    amplified = refine_sparse_embedding(_refinement_input(amplification=8))

    baseline_edge = next(
        edge
        for edge in baseline.interaction_edges
        if {edge.user_id_a, edge.user_id_b} == {"Eleanor", "Winston"}
    )
    amplified_edge = next(
        edge
        for edge in amplified.interaction_edges
        if {edge.user_id_a, edge.user_id_b} == {"Eleanor", "Winston"}
    )

    baseline_pull = baseline_edge.final_weight * 0.08
    amplified_pull = amplified_edge.final_weight * 0.08
    assert amplified_pull > baseline_pull
    assert amplified_edge.sensitivity_multiplier > baseline_edge.sensitivity_multiplier


def test_pipeline_clips_movement_under_stronger_sensitivity(monkeypatch):
    users = [
        _make_user(
            uid=f"u{i:02d}",
            interests=["music", "reading"] if i % 2 == 0 else ["travel", "sports"],
            age=22 + i,
        )
        for i in range(10)
    ]
    user_ids = [u.id for u in users]
    base_coordinates = np.array([[float(i), float(i % 3)] for i in range(10)], dtype=float)

    def _fake_embedding(_input):
        return SparseEmbeddingResult(
            user_ids=user_ids,
            coordinates=base_coordinates.copy(),
            profile_edges=[],
        )

    monkeypatch.setattr("services.map_pipeline.pipeline.build_sparse_profile_embedding", _fake_embedding)

    heavy_counts = {
        ("u00", "u01"): {"likes": 200, "comments": 120, "dms": 80},
        ("u02", "u03"): {"likes": 170, "comments": 90, "dms": 60},
        ("u04", "u05"): {"likes": 140, "comments": 80, "dms": 55},
    }
    prior = {uid: (0.0, 0.0) for uid in user_ids}
    max_movement_delta = 0.05

    result = run_pipeline(
        users,
        heavy_counts,
        requesting_user_id="u00",
        prior_coordinates=prior,
        max_movement_delta=max_movement_delta,
        interaction_sensitivity=InteractionSensitivity(
            strength_scale=1.8,
            curve_exponent=0.82,
            normalizer=7.0,
            max_weight=0.97,
        ),
    )

    clipped_deltas = np.linalg.norm(result["raw_coords"], axis=1)
    assert np.max(clipped_deltas) <= max_movement_delta + 1e-8


def test_demo_distance_curve_rank_and_force_diagnostics_trend(tmp_path):
    rows = _build_distance_curve_rows(
        output_dir=str(tmp_path),
        use_fixture_data=True,
        max_likes=1200,
        max_comments=800,
    )

    assert len(rows) >= 5
    distances = [float(row["euclidean_distance"]) for row in rows]
    ranks = [int(row["nearest_neighbor_rank"]) for row in rows]
    weighted_interactions = [float(row["weighted_interactions"]) for row in rows]

    assert all(curr <= prev + 1e-6 for prev, curr in zip(distances, distances[1:]))

    upward_rank_steps = [
        curr - prev for prev, curr in zip(ranks, ranks[1:]) if curr > prev
    ]
    assert len(upward_rank_steps) <= 1
    assert all(step <= 1 for step in upward_rank_steps)

    assert all(
        curr >= prev - 1e-9
        for prev, curr in zip(weighted_interactions, weighted_interactions[1:])
    )
    assert all("movement_explanation" in row for row in rows)


def test_sensitivity_modes_monotonic_behavior(tmp_path):
    mode_rows: dict[InteractionSensitivityMode, list[dict]] = {}
    for mode in ("natural", "strong-bounded", "uncapped"):
        mode_rows[mode] = _build_distance_curve_rows(
            output_dir=str(tmp_path),
            use_fixture_data=True,
            max_likes=1200,
            max_comments=800,
            interaction_sensitivity=InteractionSensitivity(mode=mode),
        )

    for mode, rows in mode_rows.items():
        distances = [float(row["euclidean_distance"]) for row in rows]
        weights = [float(row["final_weight"]) for row in rows]
        assert all(curr <= prev + 1e-6 for prev, curr in zip(distances, distances[1:])), mode
        assert all(curr >= prev - 1e-9 for prev, curr in zip(weights, weights[1:])), mode
        assert all(str(row["sensitivity_mode"]) == mode for row in rows)

    natural_rows = mode_rows["natural"]
    strong_rows = mode_rows["strong-bounded"]
    uncapped_rows = mode_rows["uncapped"]

    natural_distance = float(natural_rows[-1]["euclidean_distance"])
    strong_distance = float(strong_rows[-1]["euclidean_distance"])
    uncapped_distance = float(uncapped_rows[-1]["euclidean_distance"])
    assert strong_distance <= natural_distance + 1e-6
    assert uncapped_distance <= strong_distance + 1e-6

    natural_weight = float(natural_rows[-1]["final_weight"])
    strong_weight = float(strong_rows[-1]["final_weight"])
    uncapped_weight = float(uncapped_rows[-1]["final_weight"])
    assert strong_weight >= natural_weight - 1e-9
    assert uncapped_weight >= strong_weight - 1e-9
