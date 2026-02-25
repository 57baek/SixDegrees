from typing import Optional

from pydantic import BaseModel


class UserProfile(BaseModel):
    id: str
    nickname: str
    interests: list[str]
    city: str
    state: str
    age: int
    languages: list[str]
    education: str
    industry: str
    timezone: str
    occupation: Optional[str] = None
