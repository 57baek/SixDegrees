"""Phase 24 demo pipeline runner for baseline and amplified scenarios."""

from __future__ import annotations

from copy import deepcopy

from models.user import UserProfile
from scripts.seed_demo_map_data import ELEANOR_ID, WINSTON_ID, canonical_pair
from services.map_pipeline.contracts import RawInteractionCounts
from services.map_pipeline.pipeline import run_pipeline


def run_phase24_demo(
    output_dir: str = "demo/data",
    supabase=None,
) -> dict:
    """Generate baseline + amplified artifacts for notebook use."""
    client = supabase
    if client is None:
        try:
            from config.supabase import get_supabase_client
        except ModuleNotFoundError:  # compatibility for in-flight config relocation
            from models.config.supabase import get_supabase_client

        client = get_supabase_client()

    profile_rows = _fetch_demo_profiles(client)
    interaction_rows = _fetch_demo_interactions(client)
    users = _rows_to_users(profile_rows)

    baseline_counts = _interaction_rows_to_counts(interaction_rows)
    amplified_rows = _amplify_pair(interaction_rows, ELEANOR_ID, WINSTON_ID)
    amplified_counts = _interaction_rows_to_counts(amplified_rows)

    baseline_result = run_pipeline(
        users=users,
        raw_interaction_counts=baseline_counts,
        requesting_user_id=ELEANOR_ID,
    )
    amplified_result = run_pipeline(
        users=users,
        raw_interaction_counts=amplified_counts,
        requesting_user_id=ELEANOR_ID,
    )

    return {
        "metadata": {
            "output_dir": output_dir,
            "user_count": len(users),
            "requesting_user_id": ELEANOR_ID,
            "eleanor_id": ELEANOR_ID,
            "winston_id": WINSTON_ID,
        },
        "baseline": _build_variant_payload(users, baseline_result, baseline_counts),
        "amplified": _build_variant_payload(users, amplified_result, amplified_counts),
        "comparison": _build_pair_comparison(baseline_counts, amplified_counts),
    }


def _fetch_demo_profiles(client) -> list[dict]:
    response = client.table("demo_profiles").select("*").execute()
    rows = response.data or []
    return sorted(rows, key=lambda row: str(row["id"]))


def _fetch_demo_interactions(client) -> list[dict]:
    response = client.table("demo_interactions").select("*").execute()
    rows = response.data or []
    return sorted(rows, key=lambda row: (str(row["user_id_a"]), str(row["user_id_b"])))


def _rows_to_users(profile_rows: list[dict]) -> list[UserProfile]:
    users: list[UserProfile] = []
    for row in profile_rows:
        users.append(
            UserProfile(
                id=str(row["id"]),
                nickname=row["nickname"],
                interests=[str(value) for value in row.get("interests") or []],
                city=row["city"],
                state=row["state"],
                age=int(row["age"]),
                languages=[str(value) for value in row.get("languages") or []],
                education=row["education"],
                industry=row["industry"],
                timezone=row["timezone"],
                occupation=row.get("occupation"),
            )
        )
    return users


def _interaction_rows_to_counts(rows: list[dict]) -> RawInteractionCounts:
    counts: RawInteractionCounts = {}
    for row in rows:
        user_id_a = str(row["user_id_a"])
        user_id_b = str(row["user_id_b"])
        pair = canonical_pair(user_id_a, user_id_b)
        counts[pair] = {
            "likes": int(row.get("likes_count", 0)),
            "comments": int(row.get("comments_count", 0)),
            "dms": int(row.get("dm_count", 0)),
        }
    return counts


def _amplify_pair(rows: list[dict], user_id_a: str, user_id_b: str) -> list[dict]:
    target_pair = canonical_pair(user_id_a, user_id_b)
    amplified_rows = deepcopy(rows)

    for row in amplified_rows:
        pair = canonical_pair(str(row["user_id_a"]), str(row["user_id_b"]))
        if pair != target_pair:
            continue
        row["likes_count"] = int(row.get("likes_count", 0)) + 120
        row["comments_count"] = int(row.get("comments_count", 0)) + 80
        return amplified_rows

    amplified_rows.append(
        {
            "user_id_a": target_pair[0],
            "user_id_b": target_pair[1],
            "likes_count": 120,
            "comments_count": 80,
            "dm_count": 0,
        }
    )
    return sorted(
        amplified_rows,
        key=lambda row: (str(row["user_id_a"]), str(row["user_id_b"])),
    )


def _build_variant_payload(
    users: list[UserProfile],
    pipeline_result: dict,
    interaction_counts: RawInteractionCounts,
) -> dict:
    nickname_by_user_id = {user.id: user.nickname for user in users}
    user_ids = list(pipeline_result["user_ids"])
    raw_coords = pipeline_result["raw_coords"]

    global_points = []
    for index, user_id in enumerate(user_ids):
        global_points.append(
            {
                "user_id": user_id,
                "nickname": nickname_by_user_id[user_id],
                "x": float(raw_coords[index][0]),
                "y": float(raw_coords[index][1]),
            }
        )

    translated_points = [
        {
            "user_id": row["user_id"],
            "nickname": nickname_by_user_id[row["user_id"]],
            "x": float(row["x"]),
            "y": float(row["y"]),
            "tier": int(row["tier"]),
        }
        for row in pipeline_result["translated_results"]
    ]
    translated_points.sort(key=lambda row: row["user_id"])

    interactions = [
        {
            "user_id_a": pair[0],
            "user_id_b": pair[1],
            "likes": int(counts.get("likes", 0)),
            "comments": int(counts.get("comments", 0)),
            "dms": int(counts.get("dms", 0)),
        }
        for pair, counts in sorted(interaction_counts.items(), key=lambda item: item[0])
    ]

    return {
        "global_points": global_points,
        "translated_points": translated_points,
        "interactions": interactions,
    }


def _build_pair_comparison(
    baseline_counts: RawInteractionCounts,
    amplified_counts: RawInteractionCounts,
) -> dict:
    pair = canonical_pair(ELEANOR_ID, WINSTON_ID)
    baseline = baseline_counts.get(pair, {"likes": 0, "comments": 0, "dms": 0})
    amplified = amplified_counts.get(pair, {"likes": 0, "comments": 0, "dms": 0})
    return {
        "pair": {"user_id_a": pair[0], "user_id_b": pair[1]},
        "baseline": {
            "likes": int(baseline.get("likes", 0)),
            "comments": int(baseline.get("comments", 0)),
            "dms": int(baseline.get("dms", 0)),
        },
        "amplified": {
            "likes": int(amplified.get("likes", 0)),
            "comments": int(amplified.get("comments", 0)),
            "dms": int(amplified.get("dms", 0)),
        },
    }
