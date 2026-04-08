from config.settings import get_supabase_client
from models.user import UserProfile
from services.map.contracts import PipelineInput


def fetch() -> PipelineInput:
    sb = get_supabase_client()
    profiles_rows = sb.table("profiles").select("*").execute().data
    interactions_rows = sb.table("interactions").select("*").execute().data
    profiles = [UserProfile(**row) for row in profiles_rows]
    return PipelineInput(profiles=profiles, interactions=interactions_rows)
