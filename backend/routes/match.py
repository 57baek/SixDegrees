"""Match endpoint — returns top profile matches for the authenticated user.

Requires a valid Supabase JWT. Reads profiles to build similarity scores
and returns the top N most similar users (excluding the requester).
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from routes.deps import get_current_user
from config.settings import get_supabase_client
from models.user import UserProfile
from services.matching.scoring import get_top_matches

router = APIRouter(prefix="/match", tags=["match"])


@router.get("")
def get_matches(
    acting_user_id: str = Depends(get_current_user),
    top_n: int = Query(default=10, ge=1, le=100),
):
    """Return the top_n most similar users to the authenticated user."""
    sb = get_supabase_client()
    rows = sb.table("profiles").select("*").execute().data

    if not rows:
        raise HTTPException(status_code=404, detail="No profiles found")

    all_users = [UserProfile(**r) for r in rows]
    current_user = next((u for u in all_users if u.id == acting_user_id), None)

    if current_user is None:
        raise HTTPException(status_code=404, detail="Your profile was not found. Call PUT /profile first.")

    others = [u for u in all_users if u.id != acting_user_id]
    matches = get_top_matches(current_user, others, top_n)

    return {
        "matches": [
            {
                "user_id": m["user"].id,
                "nickname": m["user"].nickname,
                "similarity_score": m["similarity_score"],
            }
            for m in matches
        ]
    }
