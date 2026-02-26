from pathlib import Path
from unittest.mock import MagicMock

from services.map_pipeline import run_pipeline_for_user
from services.map_pipeline.coord_writer import write_coordinates


def _sql_contract_text() -> str:
    sql_path = (
        Path(__file__).resolve().parents[2]
        / "sql"
        / "v2_phase20_map_coordinates_global_contract.sql"
    )
    return sql_path.read_text(encoding="utf-8")


def test_sql_contract_defines_global_map_coordinates_schema():
    sql = _sql_contract_text()

    assert "CREATE TABLE IF NOT EXISTS public.map_coordinates" in sql
    assert "ADD COLUMN IF NOT EXISTS user_id UUID" in sql
    assert "ADD COLUMN IF NOT EXISTS prev_x DOUBLE PRECISION" in sql
    assert "ADD COLUMN IF NOT EXISTS prev_y DOUBLE PRECISION" in sql
    assert "ADD COLUMN IF NOT EXISTS version_date DATE" in sql
    assert "ADD CONSTRAINT map_coordinates_pkey PRIMARY KEY (user_id)" in sql
    assert "DROP COLUMN IF EXISTS center_user_id" in sql
    assert "DROP COLUMN IF EXISTS other_user_id" in sql
    assert "DROP COLUMN IF EXISTS is_current" in sql


def test_sql_contract_exposes_secured_global_coordinate_rpcs():
    sql = _sql_contract_text()

    assert "CREATE OR REPLACE FUNCTION public.upsert_global_map_coordinates" in sql
    assert "CREATE OR REPLACE FUNCTION public.get_global_map_coordinates" in sql
    assert "SECURITY DEFINER" in sql
    assert "ON CONFLICT (user_id) DO UPDATE" in sql
    assert "SET prev_x = mc.x" in sql
    assert "SET prev_x = mc.x," in sql
    assert "prev_y = mc.y" in sql


def test_write_coordinates_calls_global_upsert_rpc_with_required_fields(monkeypatch):
    mock_sb = MagicMock()
    monkeypatch.setattr("services.map_pipeline.coord_writer.get_supabase_client", lambda: mock_sb)

    translated_results = [
        {"user_id": "u-1", "x": 0.0, "y": 0.0, "tier": 1},
        {"user_id": "u-2", "x": 1.25, "y": -3.5, "tier": 2},
    ]

    write_coordinates(translated_results)

    assert mock_sb.rpc.call_count == 1
    rpc_name, payload = mock_sb.rpc.call_args.args
    assert rpc_name == "upsert_global_map_coordinates"
    assert "p_rows" in payload
    rows = payload["p_rows"]
    assert len(rows) == 2

    for row in rows:
        assert set(row.keys()) == {"user_id", "x", "y", "version_date", "computed_at"}
        assert row["user_id"].startswith("u-")
        assert isinstance(row["x"], float)
        assert isinstance(row["y"], float)
        assert isinstance(row["version_date"], str)
        assert isinstance(row["computed_at"], str)


def test_write_coordinates_uses_explicit_version_metadata(monkeypatch):
    mock_sb = MagicMock()
    monkeypatch.setattr("services.map_pipeline.coord_writer.get_supabase_client", lambda: mock_sb)

    write_coordinates(
        [{"user_id": "u-1", "x": 10.0, "y": 20.0}],
        version_date="2026-02-26",
        computed_at="2026-02-26T22:00:00+00:00",
    )

    payload = mock_sb.rpc.call_args.args[1]
    row = payload["p_rows"][0]
    assert row["version_date"] == "2026-02-26"
    assert row["computed_at"] == "2026-02-26T22:00:00+00:00"


def test_run_pipeline_for_user_passes_global_write_signature(monkeypatch):
    users = ["u-1", "u-2"]
    interactions = {("u-1", "u-2"): {"likes": 1, "comments": 0, "dms": 0}}
    pipeline_result = {
        "translated_results": [
            {"user_id": "u-1", "x": 0.0, "y": 0.0, "tier": 1},
            {"user_id": "u-2", "x": 1.0, "y": 2.0, "tier": 2},
        ]
    }

    mock_write = MagicMock()
    monkeypatch.setattr("services.map_pipeline.fetch_all", lambda: (users, interactions))
    monkeypatch.setattr(
        "services.map_pipeline.run_pipeline",
        lambda fetched_users, fetched_interactions, requesting_user_id: pipeline_result,
    )
    monkeypatch.setattr("services.map_pipeline.write_coordinates", mock_write)

    run_pipeline_for_user("u-1")

    assert mock_write.call_count == 1
    assert mock_write.call_args.args == (pipeline_result["translated_results"],)
