import math
from datetime import datetime, timezone
import numpy as np
from config.settings import get_supabase_client, MAX_POSITION_DELTA


def write(user_ids: list[str], new_coords: np.ndarray) -> None:
    sb = get_supabase_client()
    prev = {
        r["user_id"]: (r["x"], r["y"])
        for r in sb.table("user_positions").select("user_id,x,y").execute().data
    }
    rows = []
    now = datetime.now(timezone.utc).isoformat()
    for uid, (nx, ny) in zip(user_ids, new_coords):
        nx, ny = float(nx), float(ny)
        if uid in prev:
            ox, oy = prev[uid]
            delta = math.sqrt((nx - ox) ** 2 + (ny - oy) ** 2)
            if delta > MAX_POSITION_DELTA:
                scale = MAX_POSITION_DELTA / delta
                nx = ox + (nx - ox) * scale
                ny = oy + (ny - oy) * scale
        rows.append({"user_id": uid, "x": nx, "y": ny, "computed_at": now})
    sb.table("user_positions").upsert(rows).execute()
