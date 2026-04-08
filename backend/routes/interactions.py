"""Interaction write endpoints.

All endpoints require a valid Supabase JWT in the Authorization: Bearer header.
Interactions are stored in canonical pair order: user_id_a < user_id_b (enforced
by the interactions table CHECK constraint — do not pass args in the wrong order).
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from routes.deps import get_current_user
from config.settings import get_supabase_client

router = APIRouter(prefix="/interactions", tags=["interactions"])


class InteractionBody(BaseModel):
    target_user_id: str


_RESPONSE_LABELS: dict[str, str] = {
    "likes_count":    "likes",
    "comments_count": "comments",
    "dm_count":       "dms",
}


def _record_interaction(acting_user_id: str, target_user_id: str, column: str) -> dict:
    """Atomically upsert an interaction row and increment a count column via RPC.

    Enforces canonical pair ordering (user_id_a < user_id_b) before calling the
    Postgres function. The interactions table CHECK constraint rejects rows where
    user_id_a >= user_id_b — always enforce ordering here.
    """
    if acting_user_id == target_user_id:
        raise HTTPException(status_code=400, detail="Cannot interact with yourself")

    uid_a = min(acting_user_id, target_user_id)
    uid_b = max(acting_user_id, target_user_id)

    get_supabase_client().rpc(
        "increment_interaction",
        {"p_user_id_a": uid_a, "p_user_id_b": uid_b, "p_column": column},
    ).execute()

    label = _RESPONSE_LABELS.get(column, column.replace("_count", "s"))
    return {"detail": f"{label} recorded"}


@router.post("/like")
def record_like(
    body: InteractionBody,
    acting_user_id: str = Depends(get_current_user),
):
    return _record_interaction(acting_user_id, body.target_user_id, "likes_count")


@router.post("/comment")
def record_comment(
    body: InteractionBody,
    acting_user_id: str = Depends(get_current_user),
):
    return _record_interaction(acting_user_id, body.target_user_id, "comments_count")


@router.post("/dm")
def record_dm(
    body: InteractionBody,
    acting_user_id: str = Depends(get_current_user),
):
    return _record_interaction(acting_user_id, body.target_user_id, "dm_count")
