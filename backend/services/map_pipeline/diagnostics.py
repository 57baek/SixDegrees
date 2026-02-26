"""Diagnostics persistence helpers for map pipeline runs."""

from typing import Any

from config.supabase import get_supabase_client


def record_compute_run(
    *,
    run_id: str,
    requesting_user_id: str,
    version_date: str,
    computed_at: str,
    profile_count: int,
    interaction_edge_count: int,
    candidate_row_count: int,
    published: bool,
    publish_block_reason: str | None,
    gate_input_passed: bool,
    gate_embedding_passed: bool,
    gate_persistence_passed: bool,
    quality_metrics: dict[str, Any],
    stage_timings_ms: dict[str, float],
    gate_details: dict[str, Any],
) -> None:
    """Persist run diagnostics via secured service-role RPC."""
    payload = {
        "run_id": run_id,
        "requesting_user_id": requesting_user_id,
        "version_date": version_date,
        "computed_at": computed_at,
        "profile_count": profile_count,
        "interaction_edge_count": interaction_edge_count,
        "candidate_row_count": candidate_row_count,
        "published": published,
        "publish_block_reason": publish_block_reason,
        "gate_input_passed": gate_input_passed,
        "gate_embedding_passed": gate_embedding_passed,
        "gate_persistence_passed": gate_persistence_passed,
        "quality_metrics": quality_metrics,
        "stage_timings_ms": stage_timings_ms,
        "gate_details": gate_details,
    }

    sb = get_supabase_client()
    sb.rpc("record_compute_run_diagnostics", {"p_payload": payload}).execute()
