from datetime import datetime, timezone
import numpy as np
from config.settings import get_supabase_client


def write(user_ids: list[str], new_coords: np.ndarray) -> None:
    # Normalize to [0, 1] so coordinates are in a consistent space across runs.
    # UMAP's raw output is unanchored — scale, translation, and orientation can
    # differ between runs even with the same random seed.
    mn = new_coords.min(axis=0)
    mx = new_coords.max(axis=0)
    rng = np.where(mx - mn == 0, 1.0, mx - mn)
    new_coords = (new_coords - mn) / rng

    sb = get_supabase_client()
    rows = []
    now = datetime.now(timezone.utc).isoformat()
    for uid, (nx, ny) in zip(user_ids, new_coords):
        rows.append({"user_id": uid, "x": float(nx), "y": float(ny), "computed_at": now})
    sb.table("user_positions").upsert(rows).execute()
