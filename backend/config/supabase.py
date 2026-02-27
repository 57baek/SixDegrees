"""Compatibility shim for Supabase config module path."""

from models.config.supabase import SUPABASE_KEY, SUPABASE_URL, supabase as _supabase

supabase = _supabase


def get_supabase_client():
    return supabase


__all__ = ["SUPABASE_KEY", "SUPABASE_URL", "supabase", "get_supabase_client"]
