"""
CaseCommand — Telegram Channel Adapter

Receives Telegram webhook updates, extracts user messages, routes them
through the unified agent, and sends replies back via Telegram Bot API.
"""

from __future__ import annotations

import os
import logging

import httpx

logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

# Allowed Telegram user IDs (comma-separated in env). Empty = allow all.
_allowed_raw = os.environ.get("TELEGRAM_ALLOWED_USERS", "")
ALLOWED_USERS: set[int] = set()
if _allowed_raw.strip():
    ALLOWED_USERS = {int(uid.strip()) for uid in _allowed_raw.split(",") if uid.strip()}


def is_configured() -> bool:
    """Return True if Telegram integration has credentials."""
    return bool(TELEGRAM_BOT_TOKEN)


def is_authorized(user_id: int) -> bool:
    """Check if a Telegram user is allowed to interact with the bot."""
    if not ALLOWED_USERS:
        return True  # no allowlist = open (suitable for dev)
    return user_id in ALLOWED_USERS


def parse_update(update: dict) -> dict | None:
    """
    Extract a normalized message from a Telegram update payload.

    Returns None if the update is not a text message we should process.
    Returns: {"chat_id": int, "user_id": int, "username": str, "text": str}
    """
    msg = update.get("message") or update.get("edited_message")
    if not msg:
        return None

    text = msg.get("text", "").strip()
    if not text:
        return None

    chat = msg.get("chat", {})
    user = msg.get("from", {})

    return {
        "chat_id": chat.get("id"),
        "user_id": user.get("id"),
        "username": user.get("username", "unknown"),
        "first_name": user.get("first_name", ""),
        "text": text,
        "message_id": msg.get("message_id"),
    }


async def send_message(chat_id: int, text: str, reply_to: int | None = None) -> bool:
    """Send a text message back to a Telegram chat."""
    if not TELEGRAM_BOT_TOKEN:
        logger.warning("Telegram bot token not configured")
        return False

    # Telegram has a 4096 char limit per message — split if needed
    chunks = _split_message(text, max_len=4000)

    async with httpx.AsyncClient(timeout=30.0) as client:
        for i, chunk in enumerate(chunks):
            payload: dict = {
                "chat_id": chat_id,
                "text": chunk,
                "parse_mode": "Markdown",
            }
            if reply_to and i == 0:
                payload["reply_to_message_id"] = reply_to

            try:
                resp = await client.post(f"{TELEGRAM_API}/sendMessage", json=payload)
                if resp.status_code != 200:
                    # Retry without Markdown if parsing fails
                    payload.pop("parse_mode", None)
                    resp = await client.post(f"{TELEGRAM_API}/sendMessage", json=payload)
                resp.raise_for_status()
            except Exception as e:
                logger.error(f"Telegram send failed: {e}")
                return False
    return True


async def send_document(chat_id: int, file_path: str, caption: str = "") -> bool:
    """Send a document file to a Telegram chat."""
    if not TELEGRAM_BOT_TOKEN:
        return False

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            with open(file_path, "rb") as f:
                files = {"document": (os.path.basename(file_path), f)}
                data = {"chat_id": str(chat_id)}
                if caption:
                    data["caption"] = caption[:1024]
                resp = await client.post(
                    f"{TELEGRAM_API}/sendDocument", data=data, files=files
                )
                resp.raise_for_status()
                return True
        except Exception as e:
            logger.error(f"Telegram document send failed: {e}")
            return False


async def set_webhook(webhook_url: str) -> dict:
    """Register the webhook URL with Telegram."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{TELEGRAM_API}/setWebhook",
            json={"url": webhook_url, "drop_pending_updates": True},
        )
        return resp.json()


async def get_webhook_info() -> dict:
    """Get current webhook info from Telegram."""
    if not TELEGRAM_BOT_TOKEN:
        return {"ok": False, "description": "Bot token not configured"}
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            resp = await client.get(f"{TELEGRAM_API}/getWebhookInfo")
            return resp.json()
        except Exception as e:
            return {"ok": False, "description": str(e)}


async def get_bot_info() -> dict:
    """Get bot profile info from Telegram."""
    if not TELEGRAM_BOT_TOKEN:
        return {"ok": False}
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            resp = await client.get(f"{TELEGRAM_API}/getMe")
            return resp.json()
        except Exception as e:
            return {"ok": False, "description": str(e)}


def _split_message(text: str, max_len: int = 4000) -> list[str]:
    """Split a long message into chunks that fit Telegram's limit."""
    if len(text) <= max_len:
        return [text]
    chunks = []
    while text:
        if len(text) <= max_len:
            chunks.append(text)
            break
        # Try to split at a newline
        split_at = text.rfind("\n", 0, max_len)
        if split_at < max_len // 2:
            split_at = max_len
        chunks.append(text[:split_at])
        text = text[split_at:].lstrip("\n")
    return chunks
