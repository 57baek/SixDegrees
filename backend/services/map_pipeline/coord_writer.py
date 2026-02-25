"""Coordinate writer for the map pipeline.

Implements the mandatory two-step write pattern when persisting computed
map coordinates back to the map_coordinates table:

  Step 1 — Mark old rows as not current:
    UPDATE map_coordinates
    SET is_current = false
    WHERE center_user_id = <id> AND is_current = true

  Step 2 — Insert new rows with is_current = true.

Why DELETE is forbidden (STORE-02):
  Old is_current=False rows are intentionally retained for future
  animation delta computation (smooth transitions between daily map updates).
  Deleting them would lose the historical position data needed for interpolation.

The center user row:
  translated_results always includes an entry for the center user at (0.0, 0.0)
  with tier=1. This row is written to map_coordinates with
  other_user_id == center_user_id (STORE-03). Do NOT filter it out.
"""

from datetime import datetime, timezone

from config.supabase import get_supabase_client


def write_coordinates(center_user_id: str, translated_results: list[dict]) -> None:
    """Write computed map coordinates to Supabase using the two-step write pattern.

    Step 1: Marks all existing is_current=True rows for this center_user_id
            as is_current=False (retains them — never deletes).
    Step 2: Inserts new rows for every entry in translated_results with
            is_current=True, including the center user at (0.0, 0.0).

    Args:
        center_user_id: The user whose map is being written. This is the
                        perspective center — all coordinates are relative to them.
        translated_results: Output from origin_translator.translate_and_assign_tiers().
                            Each entry: {"user_id": str, "x": float, "y": float, "tier": int}
                            Must include the center user entry at (0.0, 0.0).

    Returns:
        None. Raises on Supabase error (no retry logic).
    """
    sb = get_supabase_client()

    # ── Step 1: Mark old rows as not current (STORE-01, STORE-02) ────────────
    # NEVER use .delete() — old rows are retained for animation delta (STORE-02).
    sb.rpc("archive_map_coordinates", {"p_center_user_id": center_user_id}).execute()

    # ── Step 2: Insert new rows (STORE-03) ────────────────────────────────────
    now = datetime.now(timezone.utc).isoformat()

    rows = [
        {
            "center_user_id": center_user_id,
            "other_user_id":  entry["user_id"],
            "x":              entry["x"],
            "y":              entry["y"],
            "tier":           entry["tier"],
            "computed_at":    now,
            "is_current":     True,
        }
        for entry in translated_results
        # Do NOT filter: center user entry (other_user_id == center_user_id, x=0.0, y=0.0)
        # is included in every write per STORE-03.
    ]

    sb.rpc("insert_map_coordinates", {"p_rows": rows}).execute()
