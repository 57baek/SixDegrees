"""Shared FastAPI dependencies for Phase 4 write endpoints."""

from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase_auth.errors import AuthApiError
from config.settings import get_supabase_client

# auto_error=False: prevents FastAPI from returning 403 when the Authorization
# header is absent. We handle that case explicitly below so we can return 401.
_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> str:
    """Validate the Supabase JWT from Authorization: Bearer <token> header.

    Returns:
        str: The authenticated user's UUID (response.user.id).

    Raises:
        HTTPException 401: If the Authorization header is missing, the scheme
            is not Bearer, the token is expired, or the token is invalid.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = credentials.credentials
    sb = get_supabase_client()
    try:
        response = sb.auth.get_user(token)
        if response is None or response.user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return response.user.id
    except AuthApiError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
