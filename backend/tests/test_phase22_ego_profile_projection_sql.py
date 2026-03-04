from pathlib import Path
import re


def _migration_sql() -> str:
    sql_path = (
        Path(__file__).resolve().parents[1]
        / "sql"
        / "v2_phase22_ego_profile_projection.sql"
    )
    return sql_path.read_text(encoding="utf-8")


def _returns_table_columns(sql: str) -> set[str]:
    match = re.search(
        r"RETURNS TABLE\s*\((?P<columns>.*?)\)\s*LANGUAGE",
        sql,
        flags=re.IGNORECASE | re.DOTALL,
    )
    assert match is not None

    raw_lines = [line.strip() for line in match.group("columns").splitlines()]
    column_lines = [line.rstrip(",") for line in raw_lines if line and not line.startswith("--")]
    return {line.split()[0] for line in column_lines}


def test_ego_profile_projection_rpc_exists():
    sql = _migration_sql()

    assert "CREATE OR REPLACE FUNCTION public.get_ego_map_profiles" in sql
    assert "SECURITY DEFINER" in sql
    assert "SET search_path = public" in sql


def test_ego_profile_projection_required_columns_present():
    sql = _migration_sql()
    columns = _returns_table_columns(sql)

    assert {"id", "nickname", "friends"}.issubset(columns)


def test_ego_profile_projection_excludes_sensitive_columns():
    sql = _migration_sql()
    columns = _returns_table_columns(sql)

    prohibited = {
        "age",
        "education",
        "languages",
        "occupation",
        "likes_count",
        "comments_count",
        "dm_count",
        "interactions_count",
    }

    assert prohibited.isdisjoint(columns)
