"""Records pipeline run metadata to the pipeline_runs table."""

from config.settings import get_supabase_client


def record_run(
    status: str,
    user_count: int,
    edge_count: int,
    duration_ms: int,
    error: str | None,
) -> None:
    get_supabase_client().table("pipeline_runs").insert({
        "status": status,
        "user_count": user_count,
        "edge_count": edge_count,
        "duration_ms": duration_ms,
        "error": error,
    }).execute()
