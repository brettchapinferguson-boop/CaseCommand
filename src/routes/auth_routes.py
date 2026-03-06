"""
CaseCommand — Auth & Onboarding Routes

Handles user signup, login, firm onboarding, and configuration.
"""

from __future__ import annotations

import uuid
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request

from src.models.requests import SignupRequest, LoginRequest, FirmConfigUpdate
from src.auth.jwt import CurrentUser, require_org

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/signup")
async def signup(req: SignupRequest, request: Request):
    """
    Register a new user and create their organization.

    1. Creates user in Supabase Auth
    2. Creates organization record
    3. Links user to organization
    4. Creates default firm config
    """
    db = request.app.state.supabase

    try:
        # Create user in Supabase Auth
        auth_result = db.auth.sign_up({
            "email": req.email,
            "password": req.password,
        })

        if not auth_result.user:
            raise HTTPException(status_code=400, detail="Signup failed")

        user_id = auth_result.user.id

        # Create organization
        org_id = str(uuid.uuid4())
        db.table("organizations").insert({
            "id": org_id,
            "name": req.firm_name,
            "owner_id": user_id,
            "subscription_tier": "solo",
            "subscription_status": "trialing",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }).execute()

        # Create firm config
        db.table("firm_config").insert({
            "org_id": org_id,
            "firm_name": req.firm_name,
            "attorney_name": req.attorney_name,
            "bar_number": req.bar_number,
            "jurisdiction": req.jurisdiction,
        }).execute()

        # Link user to org
        db.table("org_members").insert({
            "org_id": org_id,
            "user_id": user_id,
            "role": "owner",
        }).execute()

        # Set org_id in user's app_metadata for JWT claims
        db.auth.admin.update_user_by_id(
            user_id,
            {"app_metadata": {"org_id": org_id, "role": "owner"}},
        )

        return {
            "user_id": user_id,
            "org_id": org_id,
            "message": "Account created. Check your email to confirm.",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Signup error: %s", e)
        raise HTTPException(status_code=500, detail="Signup failed. Please try again.")


@router.post("/login")
async def login(req: LoginRequest, request: Request):
    """Authenticate and return session tokens."""
    db = request.app.state.supabase

    try:
        result = db.auth.sign_in_with_password({
            "email": req.email,
            "password": req.password,
        })

        if not result.session:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        return {
            "access_token": result.session.access_token,
            "refresh_token": result.session.refresh_token,
            "expires_in": result.session.expires_in,
            "user": {
                "id": result.user.id,
                "email": result.user.email,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Login error: %s", e)
        raise HTTPException(status_code=401, detail="Invalid credentials")


@router.get("/me")
async def get_me(user: CurrentUser, request: Request):
    """Get current user profile and org info."""
    db = request.app.state.supabase

    org_info = None
    if user.org_id:
        result = db.table("organizations").select("*").eq("id", user.org_id).execute()
        if result.data:
            org_info = result.data[0]

    return {
        "user_id": user.user_id,
        "email": user.email,
        "role": user.role,
        "organization": org_info,
    }


@router.get("/firm-config")
async def get_firm_config(user: CurrentUser, request: Request):
    """Get the firm configuration for the current user's org."""
    if not user.org_id:
        raise HTTPException(status_code=403, detail="No organization found")

    db = request.app.state.supabase
    result = db.table("firm_config").select("*").eq("org_id", user.org_id).execute()

    if not result.data:
        return {}
    return result.data[0]


@router.patch("/firm-config")
async def update_firm_config(
    update: FirmConfigUpdate,
    user: CurrentUser,
    request: Request,
):
    """Update firm configuration."""
    if not user.org_id:
        raise HTTPException(status_code=403, detail="No organization found")
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    db = request.app.state.supabase
    update_data = {k: v for k, v in update.model_dump().items() if v is not None}

    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    result = (
        db.table("firm_config")
        .update(update_data)
        .eq("org_id", user.org_id)
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=404, detail="Firm config not found")
    return result.data[0]
