from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

from copy import deepcopy

from scripts.seed_demo_map_data import ELEANOR_ID, WINSTON_ID, build_demo_dataset, canonical_pair
from scripts.run_phase24_demo_pipeline import run as run_demo_artifact_writer
from services.map_pipeline.demo_pipeline import run_phase24_demo


class _FakeResponse:
    def __init__(self, data):
        self.data = data


class _FakeTableQuery:
    def __init__(self, rows):
        self._rows = rows

    def select(self, _columns):
        return self

    def execute(self):
        return _FakeResponse(deepcopy(self._rows))


class _FakeSupabase:
    def __init__(self, profiles, interactions):
        self._table_rows = {
            "demo_profiles": profiles,
            "demo_interactions": interactions,
        }

    def table(self, table_name):
        return _FakeTableQuery(self._table_rows[table_name])


def _make_fake_supabase() -> _FakeSupabase:
    profiles, interactions, _coords = build_demo_dataset()
    return _FakeSupabase(profiles, interactions)


def test_run_phase24_demo_baseline_returns_expected_shapes():
    result = run_phase24_demo(supabase=_make_fake_supabase())

    assert result["metadata"]["user_count"] == 100
    assert result["metadata"]["requesting_user_id"] == ELEANOR_ID
    assert len(result["baseline"]["global_points"]) == 100
    assert len(result["baseline"]["translated_points"]) == 100
    assert len(result["baseline"]["interactions"]) > 0


def test_run_phase24_demo_amplified_increases_eleanor_winston_counts():
    result = run_phase24_demo(supabase=_make_fake_supabase())

    pair = canonical_pair(ELEANOR_ID, WINSTON_ID)
    pair_row = result["comparison"]["pair"]
    assert (pair_row["user_id_a"], pair_row["user_id_b"]) == pair

    baseline = result["comparison"]["baseline"]
    amplified = result["comparison"]["amplified"]
    assert amplified["likes"] > baseline["likes"]
    assert amplified["comments"] > baseline["comments"]
    assert amplified["dms"] == baseline["dms"]


def test_run_phase24_demo_artifacts_writes_expected_files(tmp_path):
    summary = run_demo_artifact_writer(
        output_dir=str(tmp_path),
        use_fixture_data=True,
    )

    expected_files = {
        "phase24_global_before.csv",
        "phase24_global_after.csv",
        "phase24_eleanor_ego_before.csv",
        "phase24_eleanor_ego_after.csv",
        "phase24_eleanor_shift.csv",
        "phase24_eleanor_side_by_side.json",
    }
    assert set(summary["generated_files"]) == expected_files

    global_before_rows = list(
        csv.DictReader((tmp_path / "phase24_global_before.csv").read_text().splitlines())
    )
    assert len(global_before_rows) == 100

    eleanor_ego_rows = list(
        csv.DictReader((tmp_path / "phase24_eleanor_ego_before.csv").read_text().splitlines())
    )
    assert len(eleanor_ego_rows) == 21

    side_by_side = json.loads((tmp_path / "phase24_eleanor_side_by_side.json").read_text())
    assert len(side_by_side["before"]) == 21
    assert len(side_by_side["after"]) == 21


def test_run_phase24_demo_runner_executes_from_repo_root(tmp_path):
    repo_root = Path(__file__).resolve().parents[3]
    command = [
        sys.executable,
        "backend/scripts/run_phase24_demo_pipeline.py",
        "--output-dir",
        str(tmp_path),
        "--use-fixture-data",
    ]
    completed = subprocess.run(
        command,
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    assert (tmp_path / "phase24_global_before.csv").exists()
