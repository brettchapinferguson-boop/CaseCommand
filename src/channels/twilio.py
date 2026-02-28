"""
CaseCommand — Twilio Channel Adapter (SMS + WhatsApp)

Receives Twilio webhook callbacks for SMS and WhatsApp messages,
routes them through the unified agent, and sends replies via Twilio API.

Twilio WhatsApp uses the same API as SMS but with "whatsapp:" prefix on
phone numbers. This adapter handles both transparently.
"""

from __future__ import annotations

import os
import logging
from urllib.parse import urlencode

import httpx

logger = logging.getLogger(__name__)

TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "")
TWILIO_PHONE_NUMBER = os.environ.get("TWILIO_PHONE_NUMBER", "")  # SMS number
TWILIO_WHATSAPP_NUMBER = os.environ.get("TWILIO_WHATSAPP_NUMBER", "")  # e.g. whatsapp:+14155238886

# Allowed phone numbers (comma-separated). Empty = allow all.
_allowed_raw = os.environ.get("TWILIO_ALLOWED_NUMBERS", "")
ALLOWED_NUMBERS: set[str] = set()
if _allowed_raw.strip():
    ALLOWED_NUMBERS = {n.strip() for n in _allowed_raw.split(",") if n.strip()}

TWILIO_API_BASE = "https://api.twilio.com/2010-04-01"


def is_configured() -> bool:
    """Return True if Twilio integration has credentials."""
    return bool(TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN)


def is_authorized(phone_number: str) -> bool:
    """Check if a phone number is allowed."""
    if not ALLOWED_NUMBERS:
        return True
    # Normalize: strip whatsapp: prefix for comparison
    normalized = phone_number.replace("whatsapp:", "")
    return normalized in ALLOWED_NUMBERS or phone_number in ALLOWED_NUMBERS


def parse_webhook(form_data: dict) -> dict | None:
    """
    Extract a normalized message from a Twilio webhook payload.

    Twilio sends form-encoded data with keys like:
      MessageSid, From, To, Body, NumMedia, etc.

    Returns None if the message is empty or invalid.
    Returns: {"from": str, "to": str, "body": str, "channel": "sms"|"whatsapp", "sid": str}
    """
    body = (form_data.get("Body") or "").strip()
    if not body:
        return None

    from_number = form_data.get("From", "")
    to_number = form_data.get("To", "")

    # Detect WhatsApp vs SMS
    channel = "whatsapp" if from_number.startswith("whatsapp:") else "sms"

    return {
        "from": from_number,
        "to": to_number,
        "body": body,
        "channel": channel,
        "sid": form_data.get("MessageSid", ""),
        "num_media": int(form_data.get("NumMedia", "0")),
    }


async def send_message(to: str, body: str, channel: str = "sms") -> bool:
    """
    Send a message via Twilio (SMS or WhatsApp).

    Args:
        to: Recipient phone number (with or without whatsapp: prefix).
        body: Message text.
        channel: "sms" or "whatsapp".
    """
    if not is_configured():
        logger.warning("Twilio not configured")
        return False

    # Determine the From number
    if channel == "whatsapp":
        from_number = TWILIO_WHATSAPP_NUMBER or f"whatsapp:{TWILIO_PHONE_NUMBER}"
        if not to.startswith("whatsapp:"):
            to = f"whatsapp:{to}"
    else:
        from_number = TWILIO_PHONE_NUMBER

    if not from_number:
        logger.error("No Twilio phone number configured for channel: %s", channel)
        return False

    url = f"{TWILIO_API_BASE}/Accounts/{TWILIO_ACCOUNT_SID}/Messages.json"

    # Twilio SMS has a 1600 char limit; WhatsApp is 4096.
    max_len = 4096 if channel == "whatsapp" else 1500
    chunks = _split_message(body, max_len=max_len)

    async with httpx.AsyncClient(timeout=30.0) as client:
        for chunk in chunks:
            payload = urlencode({
                "From": from_number,
                "To": to,
                "Body": chunk,
            })
            try:
                resp = await client.post(
                    url,
                    content=payload,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN),
                )
                if resp.status_code not in (200, 201):
                    logger.error("Twilio send failed: %s %s", resp.status_code, resp.text)
                    return False
            except Exception as e:
                logger.error("Twilio send error: %s", e)
                return False
    return True


def _split_message(text: str, max_len: int = 1500) -> list[str]:
    """Split a long message into chunks that fit the channel limit."""
    if len(text) <= max_len:
        return [text]
    chunks = []
    while text:
        if len(text) <= max_len:
            chunks.append(text)
            break
        split_at = text.rfind("\n", 0, max_len)
        if split_at < max_len // 2:
            split_at = max_len
        chunks.append(text[:split_at])
        text = text[split_at:].lstrip("\n")
    return chunks
