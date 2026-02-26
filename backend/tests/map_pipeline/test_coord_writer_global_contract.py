from pathlib import Path


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
