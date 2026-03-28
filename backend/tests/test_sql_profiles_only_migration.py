from pathlib import Path


def _migration_sql() -> str:
    sql_path = (
        Path(__file__).resolve().parents[1]
        / "sql"
        / "v2_phase26_profiles_only_reset_and_republish.sql"
    )
    return sql_path.read_text(encoding="utf-8")


def test_declares_preflight_function_for_staging_gate():
    sql = _migration_sql()

    assert "CREATE OR REPLACE FUNCTION public.phase26_profiles_only_preflight()" in sql
    assert "RAISE EXCEPTION 'Phase 26 preflight blocked: publish prerequisites missing: %'" in sql


def test_drop_guard_fails_closed_before_drop():
    sql = _migration_sql()

    assert "RAISE EXCEPTION 'Phase 26 preflight blocked: % foreign-key dependencies still reference public.user_profiles'" in sql
    assert "RAISE EXCEPTION 'Phase 26 preflight blocked: % view dependencies still reference public.user_profiles'" in sql
    assert "RAISE EXCEPTION 'Phase 26 preflight blocked: % function dependencies still reference public.user_profiles'" in sql
    assert sql.index("RAISE EXCEPTION 'Phase 26 preflight blocked: % function dependencies still reference public.user_profiles'") < sql.index("DROP TABLE public.user_profiles;")


def test_runs_preflight_before_reset_and_drop():
    sql = _migration_sql()

    preflight_call = "PERFORM public.phase26_profiles_only_preflight();"
    reset_stmt = "TRUNCATE TABLE public.map_coordinates;"
    drop_stmt = "DROP TABLE public.user_profiles;"

    assert preflight_call in sql
    assert reset_stmt in sql
    assert drop_stmt in sql
    assert sql.index(preflight_call) < sql.index(reset_stmt)
    assert sql.index(reset_stmt) < sql.index(drop_stmt)


def test_dependency_scans_cover_fk_view_and_function_catalog_paths():
    sql = _migration_sql()

    assert "FROM pg_constraint" in sql
    assert "confrelid = 'public.user_profiles'::regclass" in sql
    assert "JOIN pg_rewrite rw" in sql
    assert "AND cls.relkind IN ('v', 'm')" in sql
    assert "JOIN pg_proc proc" in sql
    assert "dep.classid = 'pg_proc'::regclass" in sql


def test_reset_notice_requires_republish_of_fresh_global_version():
    sql = _migration_sql()

    assert "Phase 26 path-B reset complete: run global republish to create fresh version_date/computed_at rows" in sql
