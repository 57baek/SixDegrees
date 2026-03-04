from pathlib import Path


def _migration_sql() -> str:
    sql_path = (
        Path(__file__).resolve().parents[1]
        / "sql"
        / "v2_phase23_trigger_validation_and_legacy_drop.sql"
    )
    return sql_path.read_text(encoding="utf-8")


def test_legacy_drop_has_fail_closed_dependency_guards():
    sql = _migration_sql()

    assert "RAISE EXCEPTION 'Legacy drop blocked: trigger/counter prerequisites missing: %'" in sql
    assert "RAISE EXCEPTION 'Legacy drop blocked: % foreign-key dependencies still reference public.user_profiles'" in sql
    assert "RAISE EXCEPTION 'Legacy drop blocked: % view dependencies still reference public.user_profiles'" in sql
    assert "RAISE EXCEPTION 'Legacy drop blocked: % function dependencies still reference public.user_profiles'" in sql
    assert sql.index("RAISE EXCEPTION 'Legacy drop blocked: % function dependencies still reference public.user_profiles'") < sql.index("DROP TABLE public.user_profiles;")


def test_legacy_drop_validates_likes_and_comments_trigger_presence():
    sql = _migration_sql()

    assert "c.relname = 'likes'" in sql
    assert "t.tgname = 'trg_likes_insert'" in sql
    assert "t.tgname = 'trg_likes_delete'" in sql
    assert "c.relname = 'comments'" in sql
    assert "t.tgname = 'trg_comments_insert'" in sql
    assert "t.tgname = 'trg_comments_delete'" in sql
    assert "NOT t.tgisinternal" in sql


def test_legacy_drop_validates_required_interaction_counter_columns():
    sql = _migration_sql()

    assert "table_name = 'interactions'" in sql
    assert "column_name = 'likes_count'" in sql
    assert "column_name = 'comments_count'" in sql


def test_legacy_drop_checks_fk_view_and_function_dependencies():
    sql = _migration_sql()

    assert "FROM pg_constraint" in sql
    assert "contype = 'f'" in sql
    assert "confrelid = 'public.user_profiles'::regclass" in sql

    assert "FROM pg_depend dep" in sql
    assert "JOIN pg_rewrite rw" in sql
    assert "AND cls.relkind IN ('v', 'm')" in sql

    assert "JOIN pg_proc proc" in sql
    assert "dep.classid = 'pg_proc'::regclass" in sql


def test_legacy_drop_is_idempotent_when_table_already_absent():
    sql = _migration_sql()

    assert "IF to_regclass('public.user_profiles') IS NULL THEN" in sql
    assert "RAISE NOTICE 'public.user_profiles does not exist; skipping legacy drop gate'" in sql
    assert "RETURN;" in sql
