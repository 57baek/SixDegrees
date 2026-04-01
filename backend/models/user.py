from pydantic import BaseModel, ConfigDict, field_validator

class UserProfile(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    nickname: str
    bio: str | None = None
    avatar_url: str | None = None
    age: int | None = None
    city: str | None = None
    state: str | None = None
    education: str | None = None
    occupation: str | None = None
    industry: str | None = None
    interests: list[str] = []
    languages: list[str] = []
    profile_tier: int = 6
    is_admin: bool = False

    @field_validator("interests", "languages", mode="before")
    @classmethod
    def coerce_none_to_empty_list(cls, v):
        return v if v is not None else []
