from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from config.supabase import get_supabase_client
from routes.deps import get_current_user
from services.map_pipeline import run_pipeline_for_user
from services.map_pipeline.ego_map import build_ego_map

router = APIRouter(prefix="/map", tags=["map"])


def _rows_from_rpc(data: object) -> list[dict[str, Any]]:
    if not isinstance(data, list):
        return []
    return [row for row in data if isinstance(row, dict)]


def _fetch_map_response(user_id: str) -> dict:
    """Shared helper: fetch global rows and build requester-centered ego map."""
    sb = get_supabase_client()
    rows = _rows_from_rpc(
        sb.rpc(
            "get_global_map_coordinates",
            {"p_user_ids": None, "p_version_date": None},
        ).execute().data
    )

    required_fields = {"user_id", "x", "y", "computed_at", "version_date"}
    valid_rows = [r for r in rows if required_fields.issubset(r)]

    if not valid_rows:
        raise HTTPException(status_code=404, detail="Map not yet computed for this user")

    profile_ids = [str(r["user_id"]) for r in valid_rows]
    profiles = _rows_from_rpc(
        sb.rpc("get_ego_map_profiles", {"p_user_ids": profile_ids}).execute().data
    )
    profile_id_set = {
        str(row["id"])
        for row in profiles
        if "id" in row and row.get("id") is not None
    }

    missing_profile_ids = sorted(set(profile_ids) - profile_id_set)
    if missing_profile_ids:
        raise HTTPException(
            status_code=503,
            detail=(
                "Map profile projection is incomplete for current coordinate batch; "
                f"missing profiles for {len(missing_profile_ids)} user(s)"
            ),
        )

    try:
        nodes = build_ego_map(
            requesting_user_id=user_id,
            coordinate_rows=valid_rows,
            profile_rows=profiles,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    requester_row = next((row for row in valid_rows if row["user_id"] == user_id), None)
    if requester_row is None:
        raise HTTPException(status_code=404, detail="Map not yet computed for this user")

    return {
        "user_id": user_id,
        "version_date": requester_row["version_date"],
        "computed_at": requester_row["computed_at"],
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


@router.get("/{user_id}")
async def get_map(
    user_id: str,
    acting_user_id: str = Depends(get_current_user),
):
    if acting_user_id != user_id:
        raise HTTPException(status_code=403, detail="You may only view your own map")
    return _fetch_map_response(user_id)


@router.post("/trigger/{user_id}")
async def trigger_map(
    user_id: str,
    acting_user_id: str = Depends(get_current_user),
):
    if acting_user_id != user_id:
        raise HTTPException(status_code=403, detail="You may only trigger your own map")
    try:
        run_pipeline_for_user(user_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return _fetch_map_response(user_id)
