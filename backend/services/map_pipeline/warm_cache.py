"""Warm cache refresh service with version-aware fallback behavior."""

from __future__ import annotations

from typing import Any

from config.supabase import get_supabase_client
from services.map_pipeline.ego_map import build_ego_map


def _rows(data: object) -> list[dict[str, Any]]:
    if not isinstance(data, list):
        return []
    return [row for row in data if isinstance(row, dict)]


def _as_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "t", "true", "yes", "y"}
    if isinstance(value, (int, float)):
        return value != 0
    return False


def _metadata_for_user(user_id: str) -> dict[str, str] | None:
    sb = get_supabase_client()
    rows = _rows(
        sb.rpc(
            "get_global_map_coordinates",
            {"p_user_ids": [user_id], "p_version_date": None},
        ).execute().data
    )
    if not rows:
        return None

    row = rows[0]
    version_date = row.get("version_date")
    computed_at = row.get("computed_at")
    if version_date is None or computed_at is None:
        return None

    return {
        "version_date": str(version_date),
        "computed_at": str(computed_at),
    }


def _last_good_metadata() -> dict[str, str] | None:
    sb = get_supabase_client()
    rows = _rows(sb.rpc("get_last_good_version", {}).execute().data)
    if not rows:
        return None
    row = rows[0]
    version_date = row.get("version_date")
    computed_at = row.get("computed_at")
    if version_date is None or computed_at is None:
        return None
    return {
        "version_date": str(version_date),
        "computed_at": str(computed_at),
    }


def _cached_metadata(user_id: str) -> dict[str, str] | None:
    sb = get_supabase_client()
    rows = _rows(sb.rpc("get_warm_map_payload", {"p_user_id": user_id}).execute().data)
    if not rows:
        return None
    row = rows[0]
    version_date = row.get("version_date")
    computed_at = row.get("computed_at")
    if version_date is None or computed_at is None:
        return None
    return {
        "version_date": str(version_date),
        "computed_at": str(computed_at),
    }


def _latest_candidate_blocked() -> bool:
    sb = get_supabase_client()
    rows = _rows(
        sb.rpc(
            "get_compute_run_diagnostics",
            {"p_run_id": None, "p_limit": 1},
        ).execute().data
    )
    if not rows:
        return False
    latest = rows[0]
    published = _as_bool(latest.get("published"))
    has_reason = bool(latest.get("publish_block_reason"))
    return (not published) and has_reason


def _build_payload(user_id: str, version_date: str | None) -> dict[str, Any] | None:
    sb = get_supabase_client()
    rows = _rows(
        sb.rpc(
            "get_global_map_coordinates",
            {"p_user_ids": None, "p_version_date": version_date},
        ).execute().data
    )
    if not rows:
        return None

    profile_ids = [row.get("user_id") for row in rows if row.get("user_id")]
    profiles = _rows(sb.rpc("get_ego_map_profiles", {"p_user_ids": profile_ids}).execute().data)

    nodes = build_ego_map(
        requesting_user_id=user_id,
        coordinate_rows=rows,
        profile_rows=profiles,
    )

    requester_row = next((row for row in rows if str(row.get("user_id")) == user_id), None)
    if requester_row is None:
        return None

    return {
        "user_id": user_id,
        "version_date": str(requester_row["version_date"]),
        "computed_at": str(requester_row["computed_at"]),
        "coordinates": [
            {
                "user_id": node.user_id,
                "x": node.x,
                "y": node.y,
                "tier": node.tier,
                "nickname": node.nickname,
                "is_suggestion": node.is_suggestion,
            }
            for node in nodes
        ],
    }


def _metadata_equal(left: dict[str, str] | None, right: dict[str, str] | None) -> bool:
    if left is None or right is None:
        return False
    return (
        left.get("version_date") == right.get("version_date")
        and left.get("computed_at") == right.get("computed_at")
    )


def refresh_warm_payload_if_stale(user_id: str) -> bool:
    """Refresh per-user warm payload only when cached metadata is stale.

    Returns:
        True if payload was refreshed, False when cache was already current or
        required metadata was unavailable.
    """
    current_metadata = _metadata_for_user(user_id)
    if current_metadata is None:
        return False

    blocked_candidate = _latest_candidate_blocked()
    target_metadata = current_metadata

    if blocked_candidate:
        fallback = _last_good_metadata()
        if fallback is not None:
            target_metadata = fallback

    cached_metadata = _cached_metadata(user_id)
    if _metadata_equal(cached_metadata, target_metadata):
        return False

    payload = _build_payload(user_id, target_metadata["version_date"])
    if payload is None:
        return False

    sb = get_supabase_client()
    sb.rpc(
        "upsert_warm_map_payload",
        {
            "p_user_id": user_id,
            "p_payload": payload,
            "p_version_date": target_metadata["version_date"],
            "p_computed_at": target_metadata["computed_at"],
        },
    ).execute()

    if not blocked_candidate:
        sb.rpc(
            "record_last_good_version",
            {
                "p_version_date": target_metadata["version_date"],
                "p_computed_at": target_metadata["computed_at"],
            },
        ).execute()

    return True
