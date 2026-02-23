"""Data fetcher for the map pipeline.

Reads all user_profiles and interactions from Supabase using the service role key
and returns them in the format expected by run_pipeline().

Field mapping notes:
  - DB column location_city  → UserProfile.city
  - DB column location_state → UserProfile.state
  - occupation is hardcoded to "" because the user_profiles table has no occupation column.
    (The UserProfile model requires this field; the DB omits it.)

Returns a tuple matching run_pipeline()'s input contract:
  (list[UserProfile], dict[tuple[str, str], dict[str, int]])

Interaction keys are canonical Python tuples (user_id_a, user_id_b) where
user_id_a < user_id_b — matching the canonical pair order enforced by the DB.
"""

from typing import Tuple

from config.supabase import get_supabase_client
from models.user import UserProfile


def fetch_all() -> Tuple[list[UserProfile], dict[tuple[str, str], dict[str, int]]]:
    """Fetch all user profiles and interaction counts from Supabase.

    Reads:
      - user_profiles table → list[UserProfile] (maps location_city→city,
        location_state→state; hardcodes occupation="" for absent DB column)
      - interactions table → dict keyed by canonical pair tuple (uid_a, uid_b)
        with values {"likes": int, "comments": int, "dms": int}

    Returns:
        Tuple of (users, raw_interaction_counts) ready to pass to run_pipeline().

    Raises:
        Exception: Propagates Supabase client errors as-is (no retry logic).
    """
    sb = get_supabase_client()

    # ── Read user profiles ────────────────────────────────────────────────────
    profile_response = sb.table("user_profiles").select("*").execute()

    users: list[UserProfile] = []
    for row in profile_response.data:
        users.append(
            UserProfile(
                id=row["user_id"],
                city=row["location_city"],        # NOT "city" — DB column is location_city
                state=row["location_state"],      # NOT "state" — DB column is location_state
                interests=row["interests"] or [], # guard None → empty list
                languages=row["languages"] or [], # guard None → empty list
                education_level=row["education_level"],
                field_of_study=row["field_of_study"],
                occupation="",                   # no occupation column in DB — hardcoded
                industry=row["industry"],
                age=row["age"],
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
            "dms":      row["dm_count"],
        }

    return (users, raw_interaction_counts)
