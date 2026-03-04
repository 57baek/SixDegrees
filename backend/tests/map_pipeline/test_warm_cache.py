from types import SimpleNamespace

from services.map_pipeline import warm_cache


class _FakeSupabase:
    def __init__(self, handlers):
        self._handlers = handlers
        self.calls = []

    def rpc(self, name, params):
        self.calls.append((name, params))
        data = self._handlers(name, params)
        return SimpleNamespace(execute=lambda: SimpleNamespace(data=data))


class _FakeNode:
    def __init__(self, user_id):
        self.user_id = user_id
        self.x = 0.0
        self.y = 0.0
        self.tier = 0
        self.nickname = f"n-{user_id}"
        self.is_suggestion = False


def test_refresh_warm_payload_if_stale_refreshes_when_metadata_is_stale(monkeypatch):
    user_id = "u1"

    def handlers(name, params):
        if name == "get_global_map_coordinates" and params["p_user_ids"] == [user_id]:
            return [{"user_id": user_id, "version_date": "2026-02-27", "computed_at": "2026-02-27T00:00:00+00:00"}]
        if name == "get_compute_run_diagnostics":
            return [{"published": True, "publish_block_reason": None}]
        if name == "get_warm_map_payload":
            return [{"user_id": user_id, "version_date": "2026-02-26", "computed_at": "2026-02-26T00:00:00+00:00"}]
        if name == "get_global_map_coordinates" and params["p_user_ids"] is None:
            return [{"user_id": user_id, "x": 1.0, "y": 2.0, "version_date": "2026-02-27", "computed_at": "2026-02-27T00:00:00+00:00"}]
        if name == "get_ego_map_profiles":
            return [{"id": user_id, "nickname": "u1", "friends": []}]
        if name in {"upsert_warm_map_payload", "record_last_good_version"}:
            return {"ok": True}
        raise AssertionError(f"Unexpected RPC: {name} {params}")

    fake_sb = _FakeSupabase(handlers)
    monkeypatch.setattr("services.map_pipeline.warm_cache.get_supabase_client", lambda: fake_sb)
    monkeypatch.setattr(
        "services.map_pipeline.warm_cache.build_ego_map",
        lambda requesting_user_id, coordinate_rows, profile_rows: [_FakeNode(requesting_user_id)],
    )

    refreshed = warm_cache.refresh_warm_payload_if_stale(user_id)

    assert refreshed is True
    upsert_calls = [call for call in fake_sb.calls if call[0] == "upsert_warm_map_payload"]
    assert len(upsert_calls) == 1
    _, upsert_params = upsert_calls[0]
    assert upsert_params["p_user_id"] == user_id
    assert upsert_params["p_version_date"] == "2026-02-27"
    assert upsert_params["p_computed_at"] == "2026-02-27T00:00:00+00:00"
    assert upsert_params["p_payload"]["version_date"] == "2026-02-27"


def test_refresh_warm_payload_if_stale_noops_when_cached_payload_is_fresh(monkeypatch):
    user_id = "u2"

    def handlers(name, params):
        if name == "get_global_map_coordinates" and params["p_user_ids"] == [user_id]:
            return [{"user_id": user_id, "version_date": "2026-02-27", "computed_at": "2026-02-27T00:00:00+00:00"}]
        if name == "get_compute_run_diagnostics":
            return [{"published": True, "publish_block_reason": None}]
        if name == "get_warm_map_payload":
            return [{"user_id": user_id, "version_date": "2026-02-27", "computed_at": "2026-02-27T00:00:00+00:00"}]
        raise AssertionError(f"Unexpected RPC: {name} {params}")

    fake_sb = _FakeSupabase(handlers)
    monkeypatch.setattr("services.map_pipeline.warm_cache.get_supabase_client", lambda: fake_sb)

    refreshed = warm_cache.refresh_warm_payload_if_stale(user_id)

    assert refreshed is False
    assert all(call[0] != "upsert_warm_map_payload" for call in fake_sb.calls)
    assert all(call[0] != "record_last_good_version" for call in fake_sb.calls)


def test_refresh_warm_payload_if_stale_uses_last_good_metadata_when_candidate_blocked(monkeypatch):
    user_id = "u3"

    def handlers(name, params):
        if name == "get_global_map_coordinates" and params["p_user_ids"] == [user_id]:
            return [{"user_id": user_id, "version_date": "2026-02-27", "computed_at": "2026-02-27T00:00:00+00:00"}]
        if name == "get_compute_run_diagnostics":
            return [{"published": False, "publish_block_reason": "gate_failed"}]
        if name == "get_last_good_version":
            return [{"version_date": "2026-02-26", "computed_at": "2026-02-26T00:00:00+00:00"}]
        if name == "get_warm_map_payload":
            return []
        if name == "get_global_map_coordinates" and params["p_user_ids"] is None:
            assert params["p_version_date"] == "2026-02-26"
            return [{"user_id": user_id, "x": 9.0, "y": 4.0, "version_date": "2026-02-26", "computed_at": "2026-02-26T00:00:00+00:00"}]
        if name == "get_ego_map_profiles":
            return [{"id": user_id, "nickname": "u3", "friends": []}]
        if name == "upsert_warm_map_payload":
            return {"ok": True}
        raise AssertionError(f"Unexpected RPC: {name} {params}")

    fake_sb = _FakeSupabase(handlers)
    monkeypatch.setattr("services.map_pipeline.warm_cache.get_supabase_client", lambda: fake_sb)
    monkeypatch.setattr(
        "services.map_pipeline.warm_cache.build_ego_map",
        lambda requesting_user_id, coordinate_rows, profile_rows: [_FakeNode(requesting_user_id)],
    )

    refreshed = warm_cache.refresh_warm_payload_if_stale(user_id)

    assert refreshed is True
    upsert_calls = [call for call in fake_sb.calls if call[0] == "upsert_warm_map_payload"]
    assert len(upsert_calls) == 1
    _, upsert_params = upsert_calls[0]
    assert upsert_params["p_version_date"] == "2026-02-26"
    assert upsert_params["p_computed_at"] == "2026-02-26T00:00:00+00:00"
    assert all(call[0] != "record_last_good_version" for call in fake_sb.calls)
