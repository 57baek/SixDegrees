"""Generate Phase 24 notebook-ready before/after demo artifacts."""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
from pathlib import Path
from typing import cast

# Allow running from any directory (not just backend/)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.seed_demo_map_data import build_demo_dataset
from services.map_pipeline.contracts import (
    InteractionSensitivity,
    InteractionSensitivityMode,
)
from services.map_pipeline.demo_pipeline import run_phase24_demo


class _FixtureResponse:
    def __init__(self, data):
        self.data = data


class _FixtureTableQuery:
    def __init__(self, rows):
        self._rows = rows

    def select(self, _columns):
        return self

    def execute(self):
        return _FixtureResponse(self._rows)


class _FixtureSupabase:
    def __init__(self, profiles, interactions):
        self._table_rows = {
            "demo_profiles": profiles,
            "demo_interactions": interactions,
        }

    def table(self, table_name):
        return _FixtureTableQuery(self._table_rows[table_name])


def run(
    output_dir: str,
    use_fixture_data: bool = False,
    amplification_likes: int = 1200,
    amplification_comments: int = 800,
    sensitivity_mode: InteractionSensitivityMode = "natural",
    sensitivity_strength_scale: float | None = None,
    sensitivity_curve_exponent: float | None = None,
    sensitivity_normalizer: float | None = None,
    sensitivity_max_weight: float | None = None,
) -> dict:
    interaction_sensitivity = InteractionSensitivity(
        mode=sensitivity_mode,
        strength_scale=sensitivity_strength_scale,
        curve_exponent=sensitivity_curve_exponent,
        normalizer=sensitivity_normalizer,
        max_weight=sensitivity_max_weight,
    )
    demo_result = _load_demo_result(
        output_dir=output_dir,
        use_fixture_data=use_fixture_data,
        amplification_likes=amplification_likes,
        amplification_comments=amplification_comments,
        interaction_sensitivity=interaction_sensitivity,
    )
    distance_curve = _build_distance_curve_rows(
        output_dir=output_dir,
        use_fixture_data=use_fixture_data,
        max_likes=amplification_likes,
        max_comments=amplification_comments,
        interaction_sensitivity=interaction_sensitivity,
    )
    artifacts = _build_artifacts(demo_result, distance_curve)
    _write_artifacts(output_dir=output_dir, artifacts=artifacts)
    return {
        "output_dir": output_dir,
        "generated_files": sorted(artifacts.keys()),
    }


def _load_demo_result(
    output_dir: str,
    use_fixture_data: bool,
    amplification_likes: int,
    amplification_comments: int,
    interaction_sensitivity: InteractionSensitivity | None = None,
) -> dict:
    if use_fixture_data:
        return run_phase24_demo(
            output_dir=output_dir,
            supabase=_build_fixture_supabase(),
            amplification_likes=amplification_likes,
            amplification_comments=amplification_comments,
            interaction_sensitivity=interaction_sensitivity,
        )

    try:
        return run_phase24_demo(
            output_dir=output_dir,
            amplification_likes=amplification_likes,
            amplification_comments=amplification_comments,
            interaction_sensitivity=interaction_sensitivity,
        )
    except Exception:
        return run_phase24_demo(
            output_dir=output_dir,
            supabase=_build_fixture_supabase(),
            amplification_likes=amplification_likes,
            amplification_comments=amplification_comments,
            interaction_sensitivity=interaction_sensitivity,
        )


def _build_fixture_supabase() -> _FixtureSupabase:
    profiles, interactions, _coordinates = build_demo_dataset()
    return _FixtureSupabase(profiles=profiles, interactions=interactions)


def _build_artifacts(
    demo_result: dict,
    distance_curve: list[dict],
) -> dict[str, list[dict] | dict]:
    baseline_global = demo_result["baseline"]["global_points"]
    amplified_global = demo_result["amplified"]["global_points"]
    baseline_translated = demo_result["baseline"]["translated_points"]
    amplified_translated = demo_result["amplified"]["translated_points"]
    baseline_local_translated = demo_result["baseline_local"]["translated_points"]
    amplified_local_translated = demo_result["amplified_local"]["translated_points"]

    eleanor_id = demo_result["metadata"]["eleanor_id"]
    eleanor_friend_ids = set(demo_result["metadata"]["eleanor_friend_ids"])
    ego_ids = {eleanor_id, *eleanor_friend_ids}

    baseline_ego = list(baseline_local_translated)
    amplified_ego = list(amplified_local_translated)

    baseline_by_user_id = {row["user_id"]: row for row in baseline_translated}
    amplified_by_user_id = {row["user_id"]: row for row in amplified_translated}

    coordinate_shift = []
    for user_id in sorted(baseline_by_user_id.keys()):
        before_row = baseline_by_user_id[user_id]
        after_row = amplified_by_user_id[user_id]
        coordinate_shift.append(
            {
                "user_id": user_id,
                "nickname": before_row["nickname"],
                "before_x": before_row["x"],
                "before_y": before_row["y"],
                "after_x": after_row["x"],
                "after_y": after_row["y"],
                "delta_x": after_row["x"] - before_row["x"],
                "delta_y": after_row["y"] - before_row["y"],
            }
        )

    return {
        "phase24_global_before.csv": baseline_global,
        "phase24_global_after.csv": amplified_global,
        "phase24_eleanor_ego_before.csv": sorted(baseline_ego, key=lambda row: row["user_id"]),
        "phase24_eleanor_ego_after.csv": sorted(amplified_ego, key=lambda row: row["user_id"]),
        "phase24_eleanor_shift.csv": coordinate_shift,
        "phase24_eleanor_winston_distance_curve.csv": distance_curve,
        "phase24_eleanor_side_by_side.json": {
            "metadata": demo_result["metadata"],
            "comparison": demo_result["comparison"],
            "before": sorted(baseline_ego, key=lambda row: row["user_id"]),
            "after": sorted(amplified_ego, key=lambda row: row["user_id"]),
        },
    }


def _build_distance_curve_rows(
    output_dir: str,
    use_fixture_data: bool,
    max_likes: int,
    max_comments: int,
    interaction_sensitivity: InteractionSensitivity | None = None,
) -> list[dict]:
    likes_levels = sorted({
        0,
        max(1, int(max_likes * 0.02)),
        max(1, int(max_likes * 0.05)),
        max(1, int(max_likes * 0.10)),
        max(1, int(max_likes * 0.25)),
        max(1, int(max_likes * 0.50)),
        max_likes,
    })

    rows: list[dict] = []
    for likes in likes_levels:
        comments = 0
        if max_likes > 0:
            comments = int(round((likes / max_likes) * max_comments))

        run_result = _load_demo_result(
            output_dir=output_dir,
            use_fixture_data=use_fixture_data,
            amplification_likes=likes,
            amplification_comments=comments,
            interaction_sensitivity=interaction_sensitivity,
        )
        distance = _pair_distance(
            run_result["amplified_local"]["translated_points"],
            "Eleanor Colvin",
            "Winston Churchill",
        )
        baseline_distance = _pair_distance(
            run_result["baseline_local"]["translated_points"],
            "Eleanor Colvin",
            "Winston Churchill",
        )
        amplified_rank = _nearest_neighbor_rank(
            run_result["amplified_local"]["translated_points"],
            "Eleanor Colvin",
            "Winston Churchill",
        )
        baseline_rank = _nearest_neighbor_rank(
            run_result["baseline_local"]["translated_points"],
            "Eleanor Colvin",
            "Winston Churchill",
        )
        eleanor_id = str(run_result["metadata"]["eleanor_id"])
        winston_id = str(run_result["metadata"]["winston_id"])
        amplified_edge = _pair_edge_diagnostics(
            run_result["amplified_local"],
            eleanor_id,
            winston_id,
        )
        baseline_edge = _pair_edge_diagnostics(
            run_result["baseline_local"],
            eleanor_id,
            winston_id,
        )
        final_weight_delta = amplified_edge["final_weight"] - baseline_edge["final_weight"]
        pull_delta = amplified_edge["effective_pull"] - baseline_edge["effective_pull"]

        rows.append(
            {
                "amplification_likes": likes,
                "amplification_comments": comments,
                "sensitivity_mode": str(run_result["metadata"].get("sensitivity_mode", "natural")),
                "euclidean_distance": distance,
                "nearest_neighbor_rank": amplified_rank,
                "distance_delta_from_baseline": distance - baseline_distance,
                "rank_delta_from_baseline": amplified_rank - baseline_rank,
                "interaction_weight": amplified_edge["interaction_weight"],
                "final_weight": amplified_edge["final_weight"],
                "weighted_interactions": amplified_edge["weighted_interactions"],
                "sensitivity_multiplier": amplified_edge["sensitivity_multiplier"],
                "effective_pull": amplified_edge["effective_pull"],
                "final_weight_delta_from_baseline": final_weight_delta,
                "effective_pull_delta_from_baseline": pull_delta,
                "movement_explanation": _movement_explanation(
                    final_weight_delta=final_weight_delta,
                    pull_delta=pull_delta,
                    rank_delta=amplified_rank - baseline_rank,
                    distance_delta=distance - baseline_distance,
                ),
            }
        )
    return rows


def _pair_distance(rows: list[dict], left_nickname: str, right_nickname: str) -> float:
    by_nickname = {row["nickname"]: row for row in rows}
    left = by_nickname[left_nickname]
    right = by_nickname[right_nickname]
    return math.dist(
        (float(left["x"]), float(left["y"])),
        (float(right["x"]), float(right["y"])),
    )


def _nearest_neighbor_rank(rows: list[dict], source_nickname: str, target_nickname: str) -> int:
    by_nickname = {row["nickname"]: row for row in rows}
    source = by_nickname[source_nickname]
    distances: list[tuple[str, float]] = []
    for row in rows:
        nickname = row["nickname"]
        if nickname == source_nickname:
            continue
        distance = math.dist(
            (float(source["x"]), float(source["y"])),
            (float(row["x"]), float(row["y"])),
        )
        distances.append((nickname, distance))

    distances.sort(key=lambda value: (value[1], value[0]))
    for index, (nickname, _distance) in enumerate(distances, start=1):
        if nickname == target_nickname:
            return index
    raise ValueError(f"Target nickname '{target_nickname}' not found in nearest-neighbor list")


def _pair_edge_diagnostics(variant_payload: dict, uid_a: str, uid_b: str) -> dict[str, float]:
    diagnostics = variant_payload.get("diagnostics") or {}
    edge_rows = diagnostics.get("interaction_edges") or []
    pair = tuple(sorted((uid_a, uid_b)))

    for edge in edge_rows:
        edge_pair = tuple(sorted((str(edge["user_id_a"]), str(edge["user_id_b"]))))
        if edge_pair != pair:
            continue
        return {
            "interaction_weight": float(edge.get("interaction_weight", 0.0)),
            "final_weight": float(edge.get("final_weight", 0.0)),
            "weighted_interactions": float(edge.get("weighted_interactions", 0.0)),
            "sensitivity_multiplier": float(edge.get("sensitivity_multiplier", 0.0)),
            "effective_pull": float(edge.get("effective_pull", 0.0)),
        }

    return {
        "interaction_weight": 0.0,
        "final_weight": 0.0,
        "weighted_interactions": 0.0,
        "sensitivity_multiplier": 0.0,
        "effective_pull": 0.0,
    }


def _movement_explanation(
    final_weight_delta: float,
    pull_delta: float,
    rank_delta: int,
    distance_delta: float,
) -> str:
    direction = "closer" if distance_delta < 0 else "farther" if distance_delta > 0 else "stable"
    rank_direction = (
        "improved"
        if rank_delta < 0
        else "worsened"
        if rank_delta > 0
        else "unchanged"
    )
    return (
        f"distance={direction}; rank={rank_direction}; "
        f"final_weight_delta={final_weight_delta:.6f}; pull_delta={pull_delta:.6f}"
    )


def _write_artifacts(output_dir: str, artifacts: dict[str, list[dict] | dict]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    for file_name, data in artifacts.items():
        destination = output_path / file_name
        if file_name.endswith(".csv"):
            if not isinstance(data, list):
                raise ValueError(f"CSV artifact '{file_name}' must be a list of rows")
            _write_csv(destination, cast(list[dict], data))
            continue
        destination.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def _write_csv(destination: Path, rows: list[dict]) -> None:
    if not rows:
        destination.write_text("", encoding="utf-8")
        return

    fieldnames = list(rows[0].keys())
    with destination.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _default_output_dir() -> str:
    repo_root = Path(__file__).resolve().parents[2]
    return str(repo_root / "demo" / "data")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default=_default_output_dir())
    parser.add_argument(
        "--use-fixture-data",
        action="store_true",
        help="Run against deterministic fixture rows instead of Supabase demo tables.",
    )
    parser.add_argument(
        "--amplification-likes",
        type=int,
        default=1200,
        help="Likes boost applied to Eleanor<->Winston interaction for amplified scenario.",
    )
    parser.add_argument(
        "--amplification-comments",
        type=int,
        default=800,
        help="Comments boost applied to Eleanor<->Winston interaction for amplified scenario.",
    )
    parser.add_argument(
        "--sensitivity-mode",
        choices=["natural", "strong-bounded", "uncapped"],
        default="natural",
        help="Interaction sensitivity preset used by the map pipeline.",
    )
    parser.add_argument(
        "--sensitivity-strength-scale",
        type=float,
        default=None,
        help="Optional override for sensitivity strength_scale.",
    )
    parser.add_argument(
        "--sensitivity-curve-exponent",
        type=float,
        default=None,
        help="Optional override for sensitivity curve_exponent.",
    )
    parser.add_argument(
        "--sensitivity-normalizer",
        type=float,
        default=None,
        help="Optional override for sensitivity normalizer.",
    )
    parser.add_argument(
        "--sensitivity-max-weight",
        type=float,
        default=None,
        help="Optional override for sensitivity max_weight cap.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    result = run(
        output_dir=args.output_dir,
        use_fixture_data=args.use_fixture_data,
        amplification_likes=args.amplification_likes,
        amplification_comments=args.amplification_comments,
        sensitivity_mode=args.sensitivity_mode,
        sensitivity_strength_scale=args.sensitivity_strength_scale,
        sensitivity_curve_exponent=args.sensitivity_curve_exponent,
        sensitivity_normalizer=args.sensitivity_normalizer,
        sensitivity_max_weight=args.sensitivity_max_weight,
    )
    print("Generated Phase 24 demo artifacts")
    print(f"  output_dir={result['output_dir']}")
    for file_name in result["generated_files"]:
        print(f"  - {file_name}")


if __name__ == "__main__":
    main()
