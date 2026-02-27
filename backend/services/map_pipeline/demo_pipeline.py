"""Phase 24 demo pipeline runner for baseline and amplified scenarios."""

from __future__ import annotations

from copy import deepcopy

from models.user import UserProfile
from scripts.seed_demo_map_data import ELEANOR_ID, WINSTON_ID, canonical_pair
from services.map_pipeline.contracts import InteractionSensitivity, RawInteractionCounts
from services.map_pipeline.pipeline import run_pipeline


def run_phase24_demo(
    output_dir: str = "demo/data",
    supabase=None,
    amplification_likes: int = 1200,
    amplification_comments: int = 800,
    interaction_sensitivity: InteractionSensitivity | None = None,
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
    eleanor_row = next(
        (row for row in profile_rows if str(row["id"]) == ELEANOR_ID),
        None,
    )
    eleanor_friend_ids = sorted(str(value) for value in (eleanor_row or {}).get("friends") or [])

    baseline_counts = _interaction_rows_to_counts(interaction_rows)
    amplified_rows = _amplify_pair(
        interaction_rows,
        ELEANOR_ID,
        WINSTON_ID,
        likes_delta=amplification_likes,
        comments_delta=amplification_comments,
    )
    amplified_counts = _interaction_rows_to_counts(amplified_rows)

    ego_ids = {ELEANOR_ID, *eleanor_friend_ids}
    local_users = [user for user in users if user.id in ego_ids]
    local_baseline_counts = _filter_counts_for_users(baseline_counts, ego_ids)
    local_amplified_counts = _filter_counts_for_users(amplified_counts, ego_ids)

    baseline_result = run_pipeline(
        users=users,
        raw_interaction_counts=baseline_counts,
        requesting_user_id=ELEANOR_ID,
        interaction_sensitivity=interaction_sensitivity,
    )
    amplified_result = run_pipeline(
        users=users,
        raw_interaction_counts=amplified_counts,
        requesting_user_id=ELEANOR_ID,
        interaction_sensitivity=interaction_sensitivity,
    )
    local_baseline_result = run_pipeline(
        users=local_users,
        raw_interaction_counts=local_baseline_counts,
        requesting_user_id=ELEANOR_ID,
        interaction_sensitivity=interaction_sensitivity,
    )
    local_amplified_result = run_pipeline(
        users=local_users,
        raw_interaction_counts=local_amplified_counts,
        requesting_user_id=ELEANOR_ID,
        interaction_sensitivity=interaction_sensitivity,
    )

    resolved_sensitivity = _resolved_sensitivity(local_amplified_result)

    return {
        "metadata": {
            "output_dir": output_dir,
            "user_count": len(users),
            "requesting_user_id": ELEANOR_ID,
            "eleanor_id": ELEANOR_ID,
            "winston_id": WINSTON_ID,
            "eleanor_friend_ids": eleanor_friend_ids,
            "amplification_likes": amplification_likes,
            "amplification_comments": amplification_comments,
            "sensitivity_mode": str(resolved_sensitivity.get("mode", "natural")),
            "interaction_sensitivity": {
                "strength_scale": float(resolved_sensitivity.get("strength_scale", 0.0)),
                "curve_exponent": float(resolved_sensitivity.get("curve_exponent", 0.0)),
                "normalizer": float(resolved_sensitivity.get("normalizer", 0.0)),
                "max_weight": float(resolved_sensitivity.get("max_weight", 0.0)),
            },
        },
        "baseline": _build_variant_payload(users, baseline_result, baseline_counts),
        "amplified": _build_variant_payload(users, amplified_result, amplified_counts),
        "baseline_local": _build_variant_payload(
            local_users,
            local_baseline_result,
            local_baseline_counts,
        ),
        "amplified_local": _build_variant_payload(
            local_users,
            local_amplified_result,
            local_amplified_counts,
        ),
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


def _amplify_pair(
    rows: list[dict],
    user_id_a: str,
    user_id_b: str,
    likes_delta: int,
    comments_delta: int,
) -> list[dict]:
    target_pair = canonical_pair(user_id_a, user_id_b)
    amplified_rows = deepcopy(rows)

    for row in amplified_rows:
        pair = canonical_pair(str(row["user_id_a"]), str(row["user_id_b"]))
        if pair != target_pair:
            continue
        row["likes_count"] = int(row.get("likes_count", 0)) + likes_delta
        row["comments_count"] = int(row.get("comments_count", 0)) + comments_delta
        return amplified_rows

    amplified_rows.append(
        {
            "user_id_a": target_pair[0],
            "user_id_b": target_pair[1],
            "likes_count": likes_delta,
            "comments_count": comments_delta,
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

    diagnostics = pipeline_result.get("diagnostics") or {}
    refinement = diagnostics.get("refinement") or {}
    interaction_edges = sorted(
        [
            {
                "user_id_a": str(edge["user_id_a"]),
                "user_id_b": str(edge["user_id_b"]),
                "interaction_weight": float(edge.get("interaction_weight", 0.0)),
                "recency_weight": float(edge.get("recency_weight", 0.0)),
                "final_weight": float(edge.get("final_weight", 0.0)),
                "weighted_interactions": float(edge.get("weighted_interactions", 0.0)),
                "sensitivity_multiplier": float(edge.get("sensitivity_multiplier", 0.0)),
                "effective_pull": float(refinement.get("step_size", 0.0))
                * float(edge.get("final_weight", 0.0)),
            }
            for edge in diagnostics.get("interaction_edges") or []
        ],
        key=lambda row: (row["user_id_a"], row["user_id_b"]),
    )

    return {
        "global_points": global_points,
        "translated_points": translated_points,
        "interactions": interactions,
        "diagnostics": {
            "refinement": {
                "step_size": float(refinement.get("step_size", 0.0)),
                "iterations": int(refinement.get("iterations", 0)),
            },
            "interaction_edges": interaction_edges,
        },
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


def _filter_counts_for_users(
    counts: RawInteractionCounts,
    allowed_user_ids: set[str],
) -> RawInteractionCounts:
    filtered: RawInteractionCounts = {}
    for (user_id_a, user_id_b), value in counts.items():
        if user_id_a in allowed_user_ids and user_id_b in allowed_user_ids:
            filtered[(user_id_a, user_id_b)] = dict(value)
    return filtered


def _resolved_sensitivity(pipeline_result: dict) -> dict[str, float | str]:
    diagnostics = pipeline_result.get("diagnostics") or {}
    refinement = diagnostics.get("refinement") or {}
    sensitivity = refinement.get("interaction_sensitivity") or {}
    return {
        "mode": str(sensitivity.get("mode", "natural")),
        "strength_scale": float(sensitivity.get("strength_scale", 0.0)),
        "curve_exponent": float(sensitivity.get("curve_exponent", 0.0)),
        "normalizer": float(sensitivity.get("normalizer", 0.0)),
        "max_weight": float(sensitivity.get("max_weight", 0.0)),
    }
