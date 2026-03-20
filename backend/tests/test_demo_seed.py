from scripts.seed_demo_map_data import (
    ELEANOR_ID,
    WINSTON_ID,
    build_demo_dataset,
    seed_demo_map_data,
)


class _FakeExecuteResult:
    def __init__(self, data):
        self.data = data


class _FakeTable:
    def __init__(self, store: dict[str, list[dict]], table_name: str):
        self._store = store
        self._table_name = table_name

    def upsert(self, rows, on_conflict=None):
        self._store[self._table_name] = rows
        return self

    def execute(self):
        return _FakeExecuteResult(self._store.get(self._table_name, []))


class _FakeSupabase:
    def __init__(self):
        self.store: dict[str, list[dict]] = {}

    def table(self, table_name: str):
        return _FakeTable(self.store, table_name)


def test_seed_demo_map_data_creates_100_profiles():
    fake = _FakeSupabase()
    result = seed_demo_map_data(fake)

    assert result["profiles"] == 100
    assert len(fake.store["demo_profiles"]) == 100
    assert len(fake.store["demo_map_coordinates"]) == 100
    assert len(fake.store["demo_interactions"]) > 0


def test_seed_demo_map_data_has_required_named_fixtures():
    profiles, _, _ = build_demo_dataset()
    by_id = {p["id"]: p for p in profiles}

    assert ELEANOR_ID in by_id
    assert WINSTON_ID in by_id
    assert by_id[ELEANOR_ID]["nickname"] == "Eleanor Colvin"
    assert by_id[WINSTON_ID]["nickname"] == "Winston Churchill"


def test_seed_demo_map_data_sets_eleanor_friends_to_exactly_20_ids():
    profiles, _, _ = build_demo_dataset()
    by_id = {p["id"]: p for p in profiles}

    eleanor = by_id[ELEANOR_ID]
    assert len(eleanor["friends"]) == 20
    assert len(set(eleanor["friends"])) == 20
    assert all(friend_id in by_id for friend_id in eleanor["friends"])


def test_seed_demo_map_data_is_deterministic_across_runs():
    first_dataset = build_demo_dataset()
    second_dataset = build_demo_dataset()

    assert first_dataset == second_dataset
