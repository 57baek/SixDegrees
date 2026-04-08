import dataclasses
from fastapi import APIRouter, Depends, HTTPException
from config.settings import get_supabase_client
from routes.deps import get_current_user
from services.map.ego import build_ego_map
from services.map.pipeline import run

router = APIRouter(prefix="/map", tags=["map"])


@router.get("/{user_id}")
async def get_map(
    user_id: str,
    acting_user_id: str = Depends(get_current_user),
):
    if acting_user_id != user_id:
        raise HTTPException(status_code=403, detail="You may only view your own map")
    response = build_ego_map(user_id)
    return dataclasses.asdict(response)


@router.post("/trigger/{user_id}")
async def trigger_map(
    user_id: str,
    acting_user_id: str = Depends(get_current_user),
):
    if acting_user_id != user_id:
        raise HTTPException(status_code=403, detail="You may only trigger your own map")
    try:
        run()
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))
    sb = get_supabase_client()
    rows = sb.table("user_positions").select("computed_at").limit(1).execute().data
    computed_at = rows[0]["computed_at"] if rows else None
    return {"status": "ok", "computed_at": computed_at}
