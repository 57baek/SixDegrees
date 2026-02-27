from __future__ import annotations

from copy import deepcopy

from scripts.seed_demo_map_data import ELEANOR_ID, WINSTON_ID, build_demo_dataset, canonical_pair
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
