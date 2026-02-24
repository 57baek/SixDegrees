"""Profile write endpoint.

Requires a valid Supabase JWT. User can only update their own profile row.
Creates the row if it does not exist (upsert on user_id PK).
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from routes.deps import get_current_user
from config.supabase import get_supabase_client

router = APIRouter(prefix="/profile", tags=["profile"])


class ProfileBody(BaseModel):
    user_id: Optional[str] = None
    display_name: Optional[str] = None
    interests: Optional[List[str]] = None
    location_city: Optional[str] = None
    location_state: Optional[str] = None
    age: Optional[int] = None
    languages: Optional[List[str]] = None
    field_of_study: Optional[str] = None
    industry: Optional[str] = None
    education_level: Optional[str] = None
    timezone: Optional[str] = None


@router.get("")
def get_profile(
    acting_user_id: str = Depends(get_current_user),
):
    result = (
        get_supabase_client()
        .table("user_profiles")
        .select("*")
        .eq("user_id", acting_user_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Profile not found")
    return result.data[0]


@router.put("")
def update_profile(
    body: ProfileBody,
    acting_user_id: str = Depends(get_current_user),
):
    # 403 guard: user cannot write another user's profile
    if body.user_id is not None and body.user_id != acting_user_id:
        raise HTTPException(status_code=403, detail="Cannot update another user's profile")

    # Build update payload from non-None fields only; always set user_id from JWT
    payload = {"user_id": acting_user_id}
    payload.update({
        k: v
        for k, v in body.model_dump().items()
        if v is not None and k != "user_id"
    })
    payload["is_onboarded"] = True  # Always set on successful profile write
    # display_name is NOT NULL — default to empty string on first insert if not supplied
    payload.setdefault("display_name", "")

    get_supabase_client().table("user_profiles").upsert(
        payload, on_conflict="user_id"
    ).execute()

    return {"detail": "Profile updated"}
