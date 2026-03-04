"""Global compute lock helpers for scheduler deduplication."""

from __future__ import annotations

from uuid import uuid4

from config.supabase import get_supabase_client

GLOBAL_COMPUTE_LOCK_KEY = "map_pipeline_global_compute"
DEFAULT_LOCK_TTL_SECONDS = 30 * 60


def _as_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "t", "true", "yes", "y"}
    if isinstance(value, (int, float)):
        return value != 0
    return False


def _extract_payload(data: object) -> dict:
    if isinstance(data, list) and data:
        first = data[0]
        if isinstance(first, dict):
            return first
    if isinstance(data, dict):
        return data
    return {}


def acquire_global_compute_lock(
    owner_token: str | None = None,
    ttl_seconds: int = DEFAULT_LOCK_TTL_SECONDS,
) -> tuple[bool, str]:
    """Attempt to acquire global compute lock.

    Returns:
        (acquired, owner_token)
    """
    if ttl_seconds <= 0:
        raise ValueError("ttl_seconds must be positive")

    lock_owner = owner_token or str(uuid4())
    sb = get_supabase_client()
    response = sb.rpc(
        "acquire_global_compute_lock",
        {
            "p_lock_key": GLOBAL_COMPUTE_LOCK_KEY,
            "p_owner_token": lock_owner,
            "p_ttl_seconds": ttl_seconds,
        },
    ).execute()

    payload = _extract_payload(getattr(response, "data", None))
    acquired = _as_bool(payload.get("acquired", payload.get("granted", False)))
    return acquired, lock_owner


def release_global_compute_lock(owner_token: str) -> bool:
    """Release global compute lock for owner token."""
    sb = get_supabase_client()
    response = sb.rpc(
        "release_global_compute_lock",
        {
            "p_lock_key": GLOBAL_COMPUTE_LOCK_KEY,
            "p_owner_token": owner_token,
        },
    ).execute()

    payload = _extract_payload(getattr(response, "data", None))
    return _as_bool(payload.get("released", payload.get("ok", False)))
