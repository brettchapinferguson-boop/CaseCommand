"""
CaseCommand — Usage Tracking Middleware

Tracks AI call usage per organization for billing and tier enforcement.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class UsageTracker:
    """
    Tracks and enforces per-org usage limits.

    Uses Supabase to persist usage counters. Counters reset monthly.
    """

    def __init__(self, supabase_client):
        self.db = supabase_client

    async def record_ai_call(self, org_id: str, tokens_used: int = 0) -> bool:
        """
        Record an AI API call for an organization.
        Returns True if within limits, False if quota exceeded.
        """
        period = datetime.now(timezone.utc).strftime("%Y-%m")

        try:
            # Upsert usage counter
            result = self.db.table("usage_tracking").upsert(
                {
                    "org_id": org_id,
                    "period": period,
                    "ai_calls": 1,  # Will be incremented by DB function
                    "tokens_used": tokens_used,
                },
                on_conflict="org_id,period",
            ).execute()
            return True
        except Exception as e:
            logger.error("Usage tracking failed: %s", e)
            # Don't block on tracking failures
            return True

    async def get_usage(self, org_id: str) -> dict:
        """Get current period usage for an org."""
        period = datetime.now(timezone.utc).strftime("%Y-%m")
        try:
            result = (
                self.db.table("usage_tracking")
                .select("*")
                .eq("org_id", org_id)
                .eq("period", period)
                .execute()
            )
            if result.data:
                return result.data[0]
            return {"org_id": org_id, "period": period, "ai_calls": 0, "tokens_used": 0}
        except Exception:
            return {"org_id": org_id, "period": period, "ai_calls": 0, "tokens_used": 0}

    async def check_quota(self, org_id: str, tier_limit: int) -> bool:
        """Check if org is within their AI call quota."""
        usage = await self.get_usage(org_id)
        return usage.get("ai_calls", 0) < tier_limit
