from fastapi import APIRouter, Depends, HTTPException
from config.supabase import get_supabase_client
from routes.deps import get_current_user
from services.map_pipeline import run_pipeline_for_user

router = APIRouter(prefix="/map", tags=["map"])


def _fetch_map_response(user_id: str) -> dict:
    """Shared helper: fetch current map_coordinates + nicknames for a user."""
    sb = get_supabase_client()
    rows = (
        sb.table("map_coordinates")
        .select("other_user_id, x, y, tier, computed_at")
        .eq("center_user_id", user_id)
        .eq("is_current", True)
        .execute()
    ).data

    if not rows:
        raise HTTPException(status_code=404, detail="Map not yet computed for this user")

    other_ids = [r["other_user_id"] for r in rows]
    profiles = (
        sb.table("profiles")
        .select("id, nickname")
        .in_("id", other_ids)
        .execute()
    ).data
    name_map = {p["id"]: p["nickname"] for p in profiles}

    return {
        "user_id": user_id,
        "computed_at": rows[0]["computed_at"],
        "coordinates": [
            {
                "user_id": r["other_user_id"],
                "x": r["x"],
                "y": r["y"],
                "tier": r["tier"],
                "nickname": name_map.get(r["other_user_id"], ""),
            }
            for r in rows
        ],
    }


@router.get("/{user_id}")
async def get_map(
    user_id: str,
    acting_user_id: str = Depends(get_current_user),
):
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
