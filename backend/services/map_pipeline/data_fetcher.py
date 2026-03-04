"""Data fetcher for the map pipeline.

Reads all profiles and interactions from Supabase using the service role key
and returns them in the format expected by run_pipeline().

Returns a tuple matching run_pipeline()'s input contract:
  (list[UserProfile], dict[tuple[str, str], dict[str, int]])

Interaction keys are canonical Python tuples (user_id_a, user_id_b) where
user_id_a < user_id_b — matching the canonical pair order enforced by the DB.
"""

from typing import Any, Tuple

from config.supabase import get_supabase_client
from models.user import UserProfile
from services.map_pipeline.contracts import RawInteractionCounts


def _require_str(row: dict[str, Any], key: str, context: str) -> str:
    value = row.get(key)
    if value is None:
        raise ValueError(f"{context} missing required field '{key}'")
    text = str(value).strip()
    if not text:
        raise ValueError(f"{context} has empty required field '{key}'")
    return text


def _coerce_int(row: dict[str, Any], key: str, context: str) -> int:
    value = row.get(key)
    if value is None:
        return 0
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{context} has invalid integer field '{key}'") from exc


def fetch_all() -> Tuple[list[UserProfile], RawInteractionCounts]:
    """Fetch all profiles and interaction counts from Supabase.

    Reads:
      - profiles table → list[UserProfile]
      - interactions table → dict keyed by canonical pair tuple (uid_a, uid_b)
        with values {"likes": int, "comments": int, "dms": int}

    Returns:
        Tuple of (users, raw_interaction_counts) ready to pass to run_pipeline().

    Raises:
        Exception: Propagates Supabase client errors as-is (no retry logic).
    """
    sb = get_supabase_client()

    # ── Read profiles ─────────────────────────────────────────────────────────
    profile_response = sb.rpc("get_all_profiles", {}).execute()

    users: list[UserProfile] = []
    profile_rows = profile_response.data if isinstance(profile_response.data, list) else []
    for index, row in enumerate(profile_rows):
        if not isinstance(row, dict):
            continue
        context = f"profiles row #{index}"
        users.append(
            UserProfile(
                id=_require_str(row, "id", context),
                nickname=row.get("nickname") or "",
                city=row.get("city") or "",
                state=row.get("state") or "",
                interests=row.get("interests") or [],
                languages=row.get("languages") or [],
                education=row.get("education") or "",
                occupation=row.get("occupation"),
                industry=row.get("industry") or "",
                age=row.get("age") or 0,
                timezone=row.get("timezone") or "UTC",
            )
        )

    # ── Read interactions ─────────────────────────────────────────────────────
    interaction_response = sb.rpc("get_all_interactions", {}).execute()

    raw_interaction_counts: RawInteractionCounts = {}
    interaction_rows = (
        interaction_response.data if isinstance(interaction_response.data, list) else []
    )
    for index, row in enumerate(interaction_rows):
        if not isinstance(row, dict):
            continue
        context = f"interactions row #{index}"
        # Keys MUST be Python tuples (not lists) — run_pipeline() uses them as dict keys.
        # DB already enforces canonical order (user_id_a < user_id_b).
        pair_key: tuple[str, str] = (
            _require_str(row, "user_id_a", context),
            _require_str(row, "user_id_b", context),
        )

        # Value keys MUST match INTERACTION_WEIGHTS in config/algorithm.py.
        raw_interaction_counts[pair_key] = {
            "likes": _coerce_int(row, "likes_count", context),
            "comments": _coerce_int(row, "comments_count", context),
            "dms": _coerce_int(row, "dm_count", context),
        }

    return (users, raw_interaction_counts)


def fetch_prior_coordinates() -> dict[str, tuple[float, float]]:
    """Fetch latest published global coordinates as prior anchors."""
    sb = get_supabase_client()
    response = sb.rpc(
        "get_global_map_coordinates",
        {"p_user_ids": None, "p_version_date": None},
    ).execute()

    prior_coordinates: dict[str, tuple[float, float]] = {}
    prior_rows = response.data if isinstance(response.data, list) else []
    for row in prior_rows:
        if not isinstance(row, dict):
            continue
        user_id = str(row.get("user_id"))
        x = row.get("x")
        y = row.get("y")
        if user_id and x is not None and y is not None:
            prior_coordinates[user_id] = (float(x), float(y))
    return prior_coordinates


def fetch_global_coordinate_rows() -> list[dict[str, Any]]:
    """Fetch current global coordinate rows for persistence verification."""
    sb = get_supabase_client()
    response = sb.rpc(
        "get_global_map_coordinates",
        {"p_user_ids": None, "p_version_date": None},
    ).execute()
    rows = response.data if isinstance(response.data, list) else []
    return [row for row in rows if isinstance(row, dict)]
