from pathlib import Path


def _migration_sql() -> str:
    sql_path = (
        Path(__file__).resolve().parents[1]
        / "sql"
        / "v2_phase23_warm_cache_and_fallback.sql"
    )
    return sql_path.read_text(encoding="utf-8")


def test_warm_cache_rpc_contract_exists():
    sql = _migration_sql()

    assert "CREATE OR REPLACE FUNCTION public.upsert_warm_map_payload" in sql
    assert "CREATE OR REPLACE FUNCTION public.get_warm_map_payload" in sql
    assert "CREATE OR REPLACE FUNCTION public.record_last_good_version" in sql
    assert "CREATE OR REPLACE FUNCTION public.get_last_good_version" in sql
    assert "SECURITY DEFINER" in sql
    assert "SET search_path = public" in sql


def test_warm_cache_tables_have_required_metadata_fields():
    sql = _migration_sql()

    assert "CREATE TABLE IF NOT EXISTS public.map_warm_payloads" in sql
    assert "payload JSONB NOT NULL" in sql
    assert "version_date DATE NOT NULL" in sql
    assert "computed_at TIMESTAMPTZ NOT NULL" in sql
    assert "updated_at TIMESTAMPTZ NOT NULL DEFAULT now()" in sql

    assert "CREATE TABLE IF NOT EXISTS public.map_last_good_version" in sql
    assert "scope TEXT PRIMARY KEY" in sql
    assert "CONSTRAINT map_last_good_version_scope_check CHECK (scope = 'global')" in sql
    assert "recorded_at TIMESTAMPTZ NOT NULL DEFAULT now()" in sql


def test_warm_cache_grants_follow_service_write_authenticated_read_scope():
    sql = _migration_sql()

    assert (
        "GRANT EXECUTE ON FUNCTION public.upsert_warm_map_payload(UUID, JSONB, DATE, TIMESTAMPTZ) TO service_role;"
        in sql
    )
    assert (
        "GRANT EXECUTE ON FUNCTION public.record_last_good_version(DATE, TIMESTAMPTZ) TO service_role;"
        in sql
    )

    assert "GRANT EXECUTE ON FUNCTION public.get_warm_map_payload(UUID) TO authenticated;" in sql
    assert "GRANT EXECUTE ON FUNCTION public.get_last_good_version() TO authenticated;" in sql
    assert "REVOKE ALL ON FUNCTION public.record_last_good_version(DATE, TIMESTAMPTZ) FROM PUBLIC;" in sql
