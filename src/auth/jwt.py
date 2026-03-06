"""
CaseCommand — JWT Authentication

Validates Supabase Auth JWTs for API requests.
Supports both:
  1. Supabase Auth JWTs (production - issued by Supabase to logged-in users)
  2. Legacy bearer token (transitional - for existing integrations)

After full migration, the legacy path will be removed.
"""

from __future__ import annotations

import logging
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from src.config import get_settings

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)


class AuthUser:
    """Authenticated user context available to all endpoints."""

    def __init__(
        self,
        user_id: str,
        org_id: str | None = None,
        email: str = "",
        role: str = "user",
    ):
        self.user_id = user_id
        self.org_id = org_id
        self.email = email
        self.role = role

    @property
    def is_admin(self) -> bool:
        return self.role in ("admin", "owner")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> AuthUser:
    """
    Extract and validate user from the Authorization header.

    Tries Supabase JWT first, falls back to legacy token.
    Raises 401 if neither works.
    """
    settings = get_settings()

    if not credentials:
        raise HTTPException(status_code=401, detail="Missing authorization header")

    token = credentials.credentials

    # --- Path 1: Legacy bearer token (transitional) ---
    if settings.AUTH_TOKEN and token == settings.AUTH_TOKEN:
        return AuthUser(user_id="legacy", org_id=None, role="admin")

    # --- Path 2: Supabase JWT ---
    if settings.SUPABASE_JWT_SECRET:
        try:
            payload = jwt.decode(
                token,
                settings.SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                audience="authenticated",
            )
            user_id = payload.get("sub", "")
            email = payload.get("email", "")
            # org_id and role come from app_metadata set during signup
            app_meta = payload.get("app_metadata", {})
            org_id = app_meta.get("org_id")
            role = app_meta.get("role", "user")

            if not user_id:
                raise HTTPException(status_code=401, detail="Invalid token: no user ID")

            return AuthUser(
                user_id=user_id,
                org_id=org_id,
                email=email,
                role=role,
            )
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError as e:
            logger.warning("JWT validation failed: %s", e)
            raise HTTPException(status_code=401, detail="Invalid token")

    # --- No valid auth method ---
    raise HTTPException(
        status_code=401,
        detail="Authentication required. Provide a valid JWT or API token.",
    )


# Type alias for dependency injection
CurrentUser = Annotated[AuthUser, Depends(get_current_user)]


def require_org(user: CurrentUser) -> AuthUser:
    """Dependency that ensures the user belongs to an organization."""
    if not user.org_id:
        raise HTTPException(
            status_code=403,
            detail="No organization associated with this account. Complete onboarding first.",
        )
    return user


def require_admin(user: CurrentUser) -> AuthUser:
    """Dependency that ensures the user is an org admin."""
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


def require_feature(feature: str):
    """
    Returns a dependency that checks whether the user's org tier includes a feature.
    Used for tier-gated endpoints.
    """
    async def _check(user: CurrentUser) -> AuthUser:
        # Feature gating is checked at the middleware/billing layer
        # This is a placeholder — the billing module will populate org tier info
        return user
    return Depends(_check)
