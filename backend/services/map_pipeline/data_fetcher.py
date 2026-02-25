"""Data fetcher for the map pipeline.

Reads all profiles and interactions from Supabase using the service role key
and returns them in the format expected by run_pipeline().

Returns a tuple matching run_pipeline()'s input contract:
  (list[UserProfile], dict[tuple[str, str], dict[str, int]])

Interaction keys are canonical Python tuples (user_id_a, user_id_b) where
user_id_a < user_id_b — matching the canonical pair order enforced by the DB.
"""

from typing import Tuple

from config.supabase import get_supabase_client
from models.user import UserProfile


def fetch_all() -> Tuple[list[UserProfile], dict[tuple[str, str], dict[str, int]]]:
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
    profile_response = sb.table("profiles").select("*").execute()

    users: list[UserProfile] = []
    for row in profile_response.data:
        users.append(
            UserProfile(
                id=row["id"],
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
    interaction_response = sb.table("interactions").select("*").execute()

    raw_interaction_counts: dict[tuple[str, str], dict[str, int]] = {}
    for row in interaction_response.data:
        # Keys MUST be Python tuples (not lists) — run_pipeline() uses them as dict keys.
        # DB already enforces canonical order (user_id_a < user_id_b).
        pair_key: tuple[str, str] = (row["user_id_a"], row["user_id_b"])

        # Value keys MUST match INTERACTION_WEIGHTS in config/algorithm.py.
        raw_interaction_counts[pair_key] = {
            "likes":    row["likes_count"],
            "comments": row["comments_count"],
            "dms":      row.get("dm_count", 0),
        }

    return (users, raw_interaction_counts)
