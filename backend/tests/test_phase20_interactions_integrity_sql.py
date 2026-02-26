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
