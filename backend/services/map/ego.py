import math
from fastapi import HTTPException
from config.settings import get_supabase_client, TIER1_K, TIER2_K
from services.map.contracts import EgoMapNode, EgoMapResponse


def build_ego_map(requester_id: str) -> EgoMapResponse:
    sb = get_supabase_client()
    positions = {
        r["user_id"]: r
        for r in sb.table("user_positions").select("*").execute().data
    }
    profiles = {
        r["id"]: r
        for r in sb.table("profiles").select("id,nickname,avatar_url").execute().data
    }

    if requester_id not in positions:
        raise HTTPException(status_code=404, detail="Map not yet computed for this user")

    rx, ry = positions[requester_id]["x"], positions[requester_id]["y"]
    computed_at = positions[requester_id]["computed_at"]

    others = []
    for uid, pos in positions.items():
        if uid == requester_id:
            continue
        tx, ty = pos["x"] - rx, pos["y"] - ry
        dist = math.sqrt(tx ** 2 + ty ** 2)
        others.append((dist, uid, tx, ty))

    others.sort(key=lambda t: t[0])

    result = []
    for rank, (_, uid, tx, ty) in enumerate(others, start=1):
        tier = 1 if rank <= TIER1_K else (2 if rank <= TIER2_K else 3)
        p = profiles.get(uid, {})
        result.append(EgoMapNode(
            user_id=uid,
            nickname=p.get("nickname", ""),
            avatar_url=p.get("avatar_url"),
            x=tx,
            y=ty,
            tier=tier,
        ))

    return EgoMapResponse(coordinates=result, computed_at=computed_at)
