from pathlib import Path


def _migration_sql() -> str:
    sql_path = (
        Path(__file__).resolve().parents[1]
        / "sql"
        / "v2_phase24_demo_tables.sql"
    )
    return sql_path.read_text(encoding="utf-8")


def test_phase24_demo_tables_exist_with_demo_only_naming():
    sql = _migration_sql()

    assert "CREATE TABLE IF NOT EXISTS public.demo_profiles" in sql
    assert "CREATE TABLE IF NOT EXISTS public.demo_interactions" in sql
    assert "CREATE TABLE IF NOT EXISTS public.demo_map_coordinates" in sql
    assert "public.profiles" not in sql
    assert "public.interactions" not in sql
    assert "public.map_coordinates" not in sql


def test_phase24_demo_interactions_enforce_canonical_pair_and_fk_guards():
    sql = _migration_sql()

    assert "CHECK (user_id_a < user_id_b)" in sql
    assert "ADD CONSTRAINT fk_demo_interactions_user_a_demo_profiles" in sql
    assert "ADD CONSTRAINT fk_demo_interactions_user_b_demo_profiles" in sql
    assert "FOREIGN KEY (user_id_a) REFERENCES public.demo_profiles(id)" in sql
    assert "FOREIGN KEY (user_id_b) REFERENCES public.demo_profiles(id)" in sql


def test_phase24_demo_contract_contains_helper_rpcs_for_profile_interaction_map_reads():
    sql = _migration_sql()

    assert "CREATE OR REPLACE FUNCTION public.get_demo_profiles" in sql
    assert "CREATE OR REPLACE FUNCTION public.get_demo_interactions" in sql
    assert "CREATE OR REPLACE FUNCTION public.get_demo_map_coordinates" in sql
    assert "SECURITY DEFINER" in sql
    assert "SET search_path = public" in sql
