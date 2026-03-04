"""Profile write endpoint.

Requires a valid Supabase JWT. User can only update their own profile row.
Creates the row if it does not exist (upsert on id PK).
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from routes.deps import get_current_user
from config.supabase import get_supabase_client

router = APIRouter(prefix="/profile", tags=["profile"])


class ProfileBody(BaseModel):
    nickname: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    education: Optional[str] = None
    occupation: Optional[str] = None
    timezone: Optional[str] = None
    interests: Optional[List[str]] = None
    languages: Optional[List[str]] = None
    industry: Optional[str] = None
    age: Optional[int] = None
    is_onboarded: Optional[bool] = None


@router.get("")
def get_profile(
    acting_user_id: str = Depends(get_current_user),
):
    result = get_supabase_client().rpc("get_profile", {"p_id": acting_user_id}).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Profile not found")
    return result.data[0]


@router.put("")
def update_profile(
    body: ProfileBody,
    acting_user_id: str = Depends(get_current_user),
):
    payload = {"id": acting_user_id}
    payload.update({
        k: v
        for k, v in body.model_dump().items()
        if v is not None
    })
    payload["is_onboarded"] = True

    p_data = {k: v for k, v in payload.items() if k != "id"}
    get_supabase_client().rpc("upsert_profile", {"p_id": acting_user_id, "p_data": p_data}).execute()

    return {"detail": "Profile updated"}
