"""
CaseCommand — Stripe Billing Service

Manages subscriptions, checkout sessions, and webhook events.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import stripe

from src.config import get_settings

logger = logging.getLogger(__name__)


class StripeService:
    """Handles Stripe subscription lifecycle."""

    def __init__(self, supabase_client):
        self.db = supabase_client
        settings = get_settings()
        stripe.api_key = settings.STRIPE_SECRET_KEY

    @property
    def is_configured(self) -> bool:
        return bool(stripe.api_key)

    async def create_checkout_session(
        self,
        org_id: str,
        price_id: str,
        success_url: str,
        cancel_url: str,
        customer_email: str = "",
    ) -> dict:
        """Create a Stripe Checkout session for a subscription."""
        if not self.is_configured:
            raise ValueError("Stripe is not configured")

        # Look up or create Stripe customer
        customer_id = await self._get_or_create_customer(org_id, customer_email)

        session = stripe.checkout.Session.create(
            customer=customer_id,
            mode="subscription",
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={"org_id": org_id},
        )

        return {"url": session.url, "session_id": session.id}

    async def create_portal_session(self, org_id: str, return_url: str) -> dict:
        """Create a Stripe Customer Portal session for managing subscriptions."""
        customer_id = await self._get_customer_id(org_id)
        if not customer_id:
            raise ValueError("No Stripe customer found for this organization")

        session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=return_url,
        )
        return {"url": session.url}

    async def handle_webhook_event(self, event: stripe.Event) -> dict:
        """Process a Stripe webhook event."""
        event_type = event["type"]
        data = event["data"]["object"]

        if event_type == "checkout.session.completed":
            return await self._handle_checkout_completed(data)
        elif event_type == "customer.subscription.updated":
            return await self._handle_subscription_updated(data)
        elif event_type == "customer.subscription.deleted":
            return await self._handle_subscription_deleted(data)
        elif event_type == "invoice.payment_failed":
            return await self._handle_payment_failed(data)

        return {"handled": False, "event_type": event_type}

    async def _handle_checkout_completed(self, session: dict) -> dict:
        org_id = session.get("metadata", {}).get("org_id")
        subscription_id = session.get("subscription")

        if org_id and subscription_id:
            sub = stripe.Subscription.retrieve(subscription_id)
            tier = self._price_to_tier(sub["items"]["data"][0]["price"]["id"])

            self.db.table("organizations").update({
                "stripe_customer_id": session.get("customer"),
                "stripe_subscription_id": subscription_id,
                "subscription_tier": tier,
                "subscription_status": "active",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }).eq("id", org_id).execute()

        return {"handled": True, "action": "subscription_activated", "org_id": org_id}

    async def _handle_subscription_updated(self, subscription: dict) -> dict:
        sub_id = subscription["id"]
        status = subscription["status"]
        tier = self._price_to_tier(subscription["items"]["data"][0]["price"]["id"])

        result = self.db.table("organizations").update({
            "subscription_tier": tier,
            "subscription_status": status,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).eq("stripe_subscription_id", sub_id).execute()

        return {"handled": True, "action": "subscription_updated"}

    async def _handle_subscription_deleted(self, subscription: dict) -> dict:
        sub_id = subscription["id"]

        self.db.table("organizations").update({
            "subscription_status": "canceled",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).eq("stripe_subscription_id", sub_id).execute()

        return {"handled": True, "action": "subscription_canceled"}

    async def _handle_payment_failed(self, invoice: dict) -> dict:
        customer_id = invoice.get("customer")
        logger.warning("Payment failed for customer: %s", customer_id)
        return {"handled": True, "action": "payment_failed"}

    async def _get_or_create_customer(self, org_id: str, email: str) -> str:
        existing = await self._get_customer_id(org_id)
        if existing:
            return existing

        customer = stripe.Customer.create(
            email=email,
            metadata={"org_id": org_id},
        )

        self.db.table("organizations").update({
            "stripe_customer_id": customer.id,
        }).eq("id", org_id).execute()

        return customer.id

    async def _get_customer_id(self, org_id: str) -> str | None:
        result = (
            self.db.table("organizations")
            .select("stripe_customer_id")
            .eq("id", org_id)
            .execute()
        )
        if result.data and result.data[0].get("stripe_customer_id"):
            return result.data[0]["stripe_customer_id"]
        return None

    def _price_to_tier(self, price_id: str) -> str:
        settings = get_settings()
        mapping = {
            settings.STRIPE_PRICE_SOLO: "solo",
            settings.STRIPE_PRICE_FIRM: "firm",
            settings.STRIPE_PRICE_ENTERPRISE: "enterprise",
        }
        return mapping.get(price_id, "solo")
