"""Generate Phase 24 notebook-ready before/after demo artifacts."""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path

# Allow running from any directory (not just backend/)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.seed_demo_map_data import build_demo_dataset
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


def run(output_dir: str, use_fixture_data: bool = False) -> dict:
    demo_result = _load_demo_result(output_dir=output_dir, use_fixture_data=use_fixture_data)
    artifacts = _build_artifacts(demo_result)
    _write_artifacts(output_dir=output_dir, artifacts=artifacts)
    return {
        "output_dir": output_dir,
        "generated_files": sorted(artifacts.keys()),
    }


def _load_demo_result(output_dir: str, use_fixture_data: bool) -> dict:
    if use_fixture_data:
        return run_phase24_demo(output_dir=output_dir, supabase=_build_fixture_supabase())

    try:
        return run_phase24_demo(output_dir=output_dir)
    except Exception:
        return run_phase24_demo(output_dir=output_dir, supabase=_build_fixture_supabase())


def _build_fixture_supabase() -> _FixtureSupabase:
    profiles, interactions, _coordinates = build_demo_dataset()
    return _FixtureSupabase(profiles=profiles, interactions=interactions)


def _build_artifacts(demo_result: dict) -> dict[str, list[dict] | dict]:
    baseline_global = demo_result["baseline"]["global_points"]
    amplified_global = demo_result["amplified"]["global_points"]
    baseline_translated = demo_result["baseline"]["translated_points"]
    amplified_translated = demo_result["amplified"]["translated_points"]

    eleanor_id = demo_result["metadata"]["eleanor_id"]
    eleanor_friend_ids = set(demo_result["metadata"]["eleanor_friend_ids"])
    ego_ids = {eleanor_id, *eleanor_friend_ids}

    baseline_ego = [row for row in baseline_translated if row["user_id"] in ego_ids]
    amplified_ego = [row for row in amplified_translated if row["user_id"] in ego_ids]

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
        "phase24_eleanor_side_by_side.json": {
            "metadata": demo_result["metadata"],
            "comparison": demo_result["comparison"],
            "before": sorted(baseline_ego, key=lambda row: row["user_id"]),
            "after": sorted(amplified_ego, key=lambda row: row["user_id"]),
        },
    }


def _write_artifacts(output_dir: str, artifacts: dict[str, list[dict] | dict]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    for file_name, data in artifacts.items():
        destination = output_path / file_name
        if file_name.endswith(".csv"):
            _write_csv(destination, data)
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
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    result = run(output_dir=args.output_dir, use_fixture_data=args.use_fixture_data)
    print("Generated Phase 24 demo artifacts")
    print(f"  output_dir={result['output_dir']}")
    for file_name in result["generated_files"]:
        print(f"  - {file_name}")


if __name__ == "__main__":
    main()
