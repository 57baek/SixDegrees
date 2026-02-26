"""Coordinate writer for the global map pipeline contract.

Writes one global row per user through the secured
``upsert_global_map_coordinates`` RPC. For each user update, the SQL contract
preserves exactly one prior snapshot by moving current ``x``/``y`` into
``prev_x``/``prev_y`` before storing the new coordinates.
"""

from datetime import datetime, timezone

from config.supabase import get_supabase_client


def write_coordinates(
    translated_results: list[dict],
    *,
    version_date: str | None = None,
    computed_at: str | None = None,
) -> None:
    """Write global map coordinates through secured RPC.

    Args:
        translated_results: Coordinate output from the pipeline where each
            entry includes ``user_id``, ``x``, and ``y``.
        version_date: Optional ``YYYY-MM-DD`` version marker. Defaults to UTC day.
        computed_at: Optional ISO timestamp shared across the batch.

    Returns:
        None. Raises on Supabase error (no retry logic).
    """
    sb = get_supabase_client()

    computed_at_value = computed_at or datetime.now(timezone.utc).isoformat()
    version_date_value = version_date or datetime.now(timezone.utc).date().isoformat()

    rows = [
        {
            "user_id": entry["user_id"],
            "x": entry["x"],
            "y": entry["y"],
            "version_date": version_date_value,
            "computed_at": computed_at_value,
        }
        for entry in translated_results
    ]

    sb.rpc("upsert_global_map_coordinates", {"p_rows": rows}).execute()
