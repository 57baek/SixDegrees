from pathlib import Path


def _migration_sql() -> str:
    sql_path = (
        Path(__file__).resolve().parents[1]
        / "sql"
        / "v2_phase20_interactions_profiles_fk_and_rebuild.sql"
    )
    return sql_path.read_text(encoding="utf-8")


def test_migration_contract_rebuilds_profile_scoped_canonical_pairs():
    sql = _migration_sql()

    assert "TRUNCATE TABLE public.interactions" in sql
    assert "FROM public.posts" in sql
    assert "FROM public.likes" in sql
    assert "FROM public.comments" in sql
    assert "JOIN profile_users" in sql
    assert "LEAST(" in sql
    assert "GREATEST(" in sql
    assert "WHERE a.user_id_a < a.user_id_b" in sql
    assert "LEFT JOIN public.profiles pa ON pa.id = i.user_id_a" in sql
    assert "LEFT JOIN public.profiles pb ON pb.id = i.user_id_b" in sql


def test_migration_contract_rebuild_has_orphan_prevention_guardrails():
    sql = _migration_sql()

    assert "RAISE EXCEPTION 'Interactions rebuild integrity check failed'" in sql
    assert "pa.id IS NULL" in sql
    assert "pb.id IS NULL" in sql
    assert "i.user_id_a >= i.user_id_b" in sql


def test_migration_contract_enforces_profiles_fk_targets_for_both_columns():
    sql = _migration_sql()

    assert "ADD CONSTRAINT fk_interactions_user_a_profiles" in sql
    assert "ADD CONSTRAINT fk_interactions_user_b_profiles" in sql
    assert "FOREIGN KEY (user_id_a) REFERENCES public.profiles(id)" in sql
    assert "FOREIGN KEY (user_id_b) REFERENCES public.profiles(id)" in sql


def test_migration_contract_removes_legacy_interaction_user_profiles_fk_targets():
    sql = _migration_sql()

    assert "DROP CONSTRAINT IF EXISTS fk_interactions_user_a" in sql
    assert "DROP CONSTRAINT IF EXISTS fk_interactions_user_b" in sql
    assert "ccu.table_name = 'user_profiles'" in sql
    assert "REFERENCES public.user_profiles" not in sql
