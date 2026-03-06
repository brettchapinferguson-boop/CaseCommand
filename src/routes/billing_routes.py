"""
CaseCommand — Billing Routes

Stripe checkout, portal, webhook, and usage tracking.
"""

from __future__ import annotations

import logging

import stripe
from fastapi import APIRouter, HTTPException, Request

from src.models.requests import CreateCheckoutRequest
from src.auth.jwt import CurrentUser, require_admin
from src.config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/billing", tags=["billing"])


@router.post("/checkout")
async def create_checkout(req: CreateCheckoutRequest, user: CurrentUser, request: Request):
    """Create a Stripe Checkout session for subscribing."""
    if not user.org_id:
        raise HTTPException(status_code=403, detail="Organization required")

    stripe_svc = request.app.state.stripe_service
    if not stripe_svc or not stripe_svc.is_configured:
        raise HTTPException(status_code=503, detail="Billing not configured")

    result = await stripe_svc.create_checkout_session(
        org_id=user.org_id,
        price_id=req.price_id,
        success_url=req.success_url,
        cancel_url=req.cancel_url,
        customer_email=user.email,
    )
    return result


@router.post("/portal")
async def create_portal(user: CurrentUser, request: Request):
    """Create a Stripe Customer Portal session for managing subscription."""
    if not user.org_id:
        raise HTTPException(status_code=403, detail="Organization required")

    stripe_svc = request.app.state.stripe_service
    if not stripe_svc or not stripe_svc.is_configured:
        raise HTTPException(status_code=503, detail="Billing not configured")

    settings = get_settings()
    return_url = f"{settings.BASE_URL}/dashboard"

    result = await stripe_svc.create_portal_session(
        org_id=user.org_id,
        return_url=return_url,
    )
    return result


@router.get("/usage")
async def get_usage(user: CurrentUser, request: Request):
    """Get current billing period usage for the user's organization."""
    if not user.org_id:
        raise HTTPException(status_code=403, detail="Organization required")

    usage_tracker = request.app.state.usage_tracker
    if not usage_tracker:
        return {"ai_calls": 0, "tokens_used": 0, "period": "unknown"}

    usage = await usage_tracker.get_usage(user.org_id)
    return usage


@router.get("/subscription")
async def get_subscription(user: CurrentUser, request: Request):
    """Get current subscription details."""
    if not user.org_id:
        raise HTTPException(status_code=403, detail="Organization required")

    db = request.app.state.supabase
    result = (
        db.table("organizations")
        .select("subscription_tier, subscription_status, stripe_customer_id")
        .eq("id", user.org_id)
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=404, detail="Organization not found")

    org = result.data[0]
    settings = get_settings()
    tier_info = settings.TIERS.get(org.get("subscription_tier", "solo"), settings.TIERS["solo"])

    return {
        "tier": org.get("subscription_tier", "solo"),
        "status": org.get("subscription_status", "inactive"),
        "tier_info": tier_info,
    }


@router.post("/webhook")
async def stripe_webhook(request: Request):
    """
    Stripe webhook endpoint. Verifies signature and processes events.
    No auth header required -- uses Stripe signature verification.
    """
    settings = get_settings()
    if not settings.STRIPE_WEBHOOK_SECRET:
        raise HTTPException(status_code=503, detail="Webhook not configured")

    body = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(
            body, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    stripe_svc = request.app.state.stripe_service
    result = await stripe_svc.handle_webhook_event(event)
    return result
