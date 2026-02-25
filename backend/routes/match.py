"""Match endpoint — returns top profile matches for the authenticated user.

Requires a valid Supabase JWT. Reads profiles to build similarity scores
and returns the top N most similar users (excluding the requester).
"""

from fastapi import APIRouter, Depends, HTTPException
from routes.deps import get_current_user
from config.supabase import get_supabase_client
from models.user import UserProfile

router = APIRouter(prefix="/match", tags=["match"])


@router.get("")
def get_matches(
    acting_user_id: str = Depends(get_current_user),
    top_n: int = 10,
):
    """Return the top_n most similar users to the authenticated user."""
    sb = get_supabase_client()
    rows = sb.table("profiles").select("*").execute().data

    if not rows:
        raise HTTPException(status_code=404, detail="No profiles found")

    # Build UserProfile objects from DB rows
    users = []
    user_index = None
    for i, row in enumerate(rows):
        up = UserProfile(
            id=row["id"],
            nickname=row.get("nickname") or "",
            interests=row.get("interests") or [],
            city=row.get("city") or "",
            state=row.get("state") or "",
            age=row.get("age") or 0,
            languages=row.get("languages") or [],
            education=row.get("education") or "",
            industry=row.get("industry") or "",
            timezone=row.get("timezone") or "UTC",
            occupation=row.get("occupation"),
        )
        users.append(up)
        if row["id"] == acting_user_id:
            user_index = i

    if user_index is None:
        raise HTTPException(status_code=404, detail="Your profile was not found. Call PUT /profile first.")

    from services.matching.scoring import build_similarity_matrix, apply_weights, similarity_to_distance

    sim_matrix = build_similarity_matrix(users)
    weighted = apply_weights(sim_matrix)
    dist_matrix = similarity_to_distance(weighted)

    # Get similarity scores for the acting user (1 - distance = similarity)
    similarity_row = 1.0 - dist_matrix[user_index]

    # Build result list: all users except the acting user, sorted by descending similarity
    results = []
    for i, user in enumerate(users):
        if i == user_index:
            continue
        results.append({
            "user_id": user.id,
            "nickname": rows[i].get("nickname") or "",
            "similarity_score": round(float(similarity_row[i]), 4),
        })

    results.sort(key=lambda x: x["similarity_score"], reverse=True)
    return {"matches": results[:top_n]}
