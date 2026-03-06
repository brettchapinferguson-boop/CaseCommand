"""
CaseCommand — Centralized Configuration

All environment variables and app settings in one place.
Validates required vars at startup, provides typed access.
"""

import os
from pathlib import Path
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Application settings loaded from environment variables."""

    # --- Core ---
    APP_NAME: str = "CaseCommand"
    BASE_URL: str = os.environ.get("BASE_URL", "").rstrip("/")
    DEBUG: bool = os.environ.get("DEBUG", "false").lower() == "true"

    # --- Anthropic ---
    ANTHROPIC_API_KEY: str = os.environ.get("ANTHROPIC_API_KEY", "")
    CLAUDE_MODEL: str = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")
    ANTHROPIC_BASE_URL: str = "https://api.anthropic.com/v1"

    # --- Voyage AI (embeddings) ---
    VOYAGE_API_KEY: str = os.environ.get("VOYAGE_API_KEY", "")

    # --- Supabase ---
    SUPABASE_URL: str = os.environ.get("SUPABASE_URL", "")
    SUPABASE_SECRET_KEY: str = (
        os.environ.get("SUPABASE_SECRET_KEY", "")
        or os.environ.get("SUPABASE_SERVICE_KEY", "")
        or os.environ.get("SUPABASE_KEY", "")
    )
    SUPABASE_JWT_SECRET: str = os.environ.get("SUPABASE_JWT_SECRET", "")

    # --- Legacy auth (to be removed after migration) ---
    AUTH_TOKEN: str = os.environ.get("AUTH_TOKEN", "")

    # --- Stripe ---
    STRIPE_SECRET_KEY: str = os.environ.get("STRIPE_SECRET_KEY", "")
    STRIPE_WEBHOOK_SECRET: str = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
    STRIPE_PRICE_SOLO: str = os.environ.get("STRIPE_PRICE_SOLO", "")
    STRIPE_PRICE_FIRM: str = os.environ.get("STRIPE_PRICE_FIRM", "")
    STRIPE_PRICE_ENTERPRISE: str = os.environ.get("STRIPE_PRICE_ENTERPRISE", "")

    # --- Telegram ---
    TELEGRAM_BOT_TOKEN: str = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_ALLOWED_USERS: str = os.environ.get("TELEGRAM_ALLOWED_USERS", "")

    # --- Twilio ---
    TWILIO_ACCOUNT_SID: str = os.environ.get("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN: str = os.environ.get("TWILIO_AUTH_TOKEN", "")
    TWILIO_PHONE_NUMBER: str = os.environ.get("TWILIO_PHONE_NUMBER", "")
    TWILIO_WHATSAPP_NUMBER: str = os.environ.get("TWILIO_WHATSAPP_NUMBER", "")
    TWILIO_ALLOWED_NUMBERS: str = os.environ.get("TWILIO_ALLOWED_NUMBERS", "")

    # --- Rate Limiting ---
    RATE_LIMIT_CHAT: str = os.environ.get("RATE_LIMIT_CHAT", "30/minute")
    RATE_LIMIT_AI: str = os.environ.get("RATE_LIMIT_AI", "20/minute")
    RATE_LIMIT_DEFAULT: str = os.environ.get("RATE_LIMIT_DEFAULT", "60/minute")

    # --- Paths ---
    PROJECT_ROOT: Path = Path(__file__).parent.parent
    SOUL_PATH: Path = PROJECT_ROOT / "SOUL.md"

    # --- Subscription Tiers ---
    TIERS = {
        "solo": {
            "name": "Solo",
            "max_users": 1,
            "monthly_ai_calls": 500,
            "features": ["chat", "documents", "discovery", "cases"],
        },
        "firm": {
            "name": "Firm",
            "max_users": 5,
            "monthly_ai_calls": 2000,
            "features": [
                "chat", "documents", "discovery", "cases",
                "trial_prep", "settlement", "channels", "outlines",
            ],
        },
        "enterprise": {
            "name": "Enterprise",
            "max_users": -1,  # unlimited
            "monthly_ai_calls": 10000,
            "features": [
                "chat", "documents", "discovery", "cases",
                "trial_prep", "settlement", "channels", "outlines",
                "nightly_agents", "api_access", "priority_support",
            ],
        },
    }

    def validate_required(self) -> list[str]:
        """Return list of missing required env vars."""
        missing = []
        if not self.ANTHROPIC_API_KEY:
            missing.append("ANTHROPIC_API_KEY")
        if not self.SUPABASE_URL:
            missing.append("SUPABASE_URL")
        if not self.SUPABASE_SECRET_KEY:
            missing.append("SUPABASE_SECRET_KEY (or SUPABASE_SERVICE_KEY)")
        return missing

    def get_proxy(self) -> str | None:
        p = (
            os.environ.get("HTTPS_PROXY")
            or os.environ.get("https_proxy")
            or os.environ.get("HTTP_PROXY")
            or os.environ.get("http_proxy")
        )
        return p if p and not p.startswith("socks") else None


@lru_cache()
def get_settings() -> Settings:
    return Settings()
