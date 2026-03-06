"""
CaseCommand — Channel Management Routes

Telegram, Twilio webhook endpoints and channel status.
"""

from __future__ import annotations

import os
import logging

from fastapi import APIRouter, HTTPException, Request, BackgroundTasks
from fastapi.responses import HTMLResponse

from src.auth.jwt import CurrentUser
from src.agent import process_message
from src.storage.documents import DocumentStore
from src.channels import telegram as tg_channel
from src.channels import twilio as tw_channel
from src.routes.chat_routes import _handle_agent_response

logger = logging.getLogger(__name__)

router = APIRouter(tags=["channels"])


# ---------------------------------------------------------------------------
# Telegram
# ---------------------------------------------------------------------------


@router.post("/webhook/telegram")
async def telegram_webhook(request: Request, background_tasks: BackgroundTasks):
    """Receive Telegram updates via webhook."""
    if not tg_channel.is_configured():
        raise HTTPException(status_code=503, detail="Telegram not configured")

    try:
        update = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    parsed = tg_channel.parse_update(update)
    if not parsed:
        return {"ok": True}

    if not tg_channel.is_authorized(parsed["user_id"]):
        await tg_channel.send_message(
            parsed["chat_id"],
            "You are not authorized to use CaseCommand. Contact your administrator.",
            reply_to=parsed["message_id"],
        )
        return {"ok": True}

    background_tasks.add_task(
        _process_telegram_message,
        request.app,
        parsed["chat_id"],
        parsed["text"],
        parsed["message_id"],
    )
    return {"ok": True}


async def _process_telegram_message(app, chat_id: int, text: str, reply_to: int):
    """Background task: run agent and reply on Telegram."""
    try:
        ctx = {"supabase": app.state.supabase}
        response = await process_message(text, context=ctx)
        doc_store: DocumentStore = app.state.doc_store
        reply_text, document = _handle_agent_response(response, text, doc_store, None)

        await tg_channel.send_message(chat_id, reply_text, reply_to=reply_to)

        if document:
            from src.storage.documents import LOCAL_DIR
            filepath = LOCAL_DIR / document["filename"]
            if filepath.exists():
                await tg_channel.send_document(
                    chat_id, str(filepath), caption=document["title"]
                )
    except Exception as e:
        logger.error("Telegram processing error: %s", e)
        await tg_channel.send_message(
            chat_id,
            "Sorry, I encountered an error processing your request. Please try again.",
            reply_to=reply_to,
        )


# ---------------------------------------------------------------------------
# Twilio
# ---------------------------------------------------------------------------


@router.post("/webhook/twilio")
async def twilio_webhook(request: Request, background_tasks: BackgroundTasks):
    """Receive Twilio SMS/WhatsApp webhook callbacks."""
    if not tw_channel.is_configured():
        raise HTTPException(status_code=503, detail="Twilio not configured")

    # Validate Twilio request signature
    if not await _verify_twilio_signature(request):
        raise HTTPException(status_code=403, detail="Invalid Twilio signature")

    try:
        form = await request.form()
        form_data = dict(form)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid form data")

    parsed = tw_channel.parse_webhook(form_data)
    if not parsed:
        return {"ok": True}

    if not tw_channel.is_authorized(parsed["from"]):
        await tw_channel.send_message(
            parsed["from"],
            "You are not authorized to use CaseCommand.",
            channel=parsed["channel"],
        )
        return HTMLResponse(content="<Response></Response>", media_type="application/xml")

    background_tasks.add_task(
        _process_twilio_message,
        request.app,
        parsed["from"],
        parsed["body"],
        parsed["channel"],
    )
    return HTMLResponse(content="<Response></Response>", media_type="application/xml")


async def _verify_twilio_signature(request: Request) -> bool:
    """Verify Twilio webhook request signature."""
    auth_token = tw_channel.TWILIO_AUTH_TOKEN
    if not auth_token:
        return True  # Skip in dev if no auth token

    sig = request.headers.get("X-Twilio-Signature", "")
    if not sig:
        return False

    try:
        from twilio.request_validator import RequestValidator
        validator = RequestValidator(auth_token)
        form = await request.form()
        url = str(request.url)
        return validator.validate(url, dict(form), sig)
    except ImportError:
        # twilio package not installed -- skip validation
        logger.warning("twilio package not installed; skipping signature validation")
        return True
    except Exception as e:
        logger.warning("Twilio signature validation failed: %s", e)
        return False


async def _process_twilio_message(app, from_number: str, text: str, channel: str):
    """Background task: run agent and reply via Twilio SMS/WhatsApp."""
    try:
        ctx = {"supabase": app.state.supabase}
        response = await process_message(text, context=ctx)
        doc_store: DocumentStore = app.state.doc_store
        reply_text, document = _handle_agent_response(response, text, doc_store, None)

        if document:
            base_url = os.environ.get("BASE_URL", "").rstrip("/")
            if base_url:
                reply_text = reply_text.replace(document["url"], f"{base_url}{document['url']}")

        await tw_channel.send_message(from_number, reply_text, channel=channel)
    except Exception as e:
        logger.error("Twilio processing error: %s", e)
        await tw_channel.send_message(
            from_number, "Sorry, I encountered an error. Please try again.", channel=channel
        )


# ---------------------------------------------------------------------------
# Channel Setup & Status
# ---------------------------------------------------------------------------


@router.post("/api/v1/channels/telegram/setup")
async def setup_telegram(user: CurrentUser, request: Request):
    """Register the Telegram webhook. Call once after deployment."""
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    if not tg_channel.is_configured():
        raise HTTPException(status_code=400, detail="TELEGRAM_BOT_TOKEN not set")

    base_url = os.environ.get("BASE_URL", "").rstrip("/")
    if not base_url:
        raise HTTPException(status_code=400, detail="BASE_URL env var not set")

    result = await tg_channel.set_webhook(f"{base_url}/webhook/telegram")
    return result


@router.get("/api/v1/channels/status")
async def channel_status(user: CurrentUser):
    """Check which messaging channels are configured."""
    tg_webhook = None
    tg_bot = None
    if tg_channel.is_configured():
        tg_webhook = await tg_channel.get_webhook_info()
        tg_bot = await tg_channel.get_bot_info()

    webhook_url = ""
    webhook_active = False
    if tg_webhook and tg_webhook.get("ok"):
        result = tg_webhook.get("result", {})
        webhook_url = result.get("url", "")
        webhook_active = bool(webhook_url)

    bot_username = ""
    if tg_bot and tg_bot.get("ok"):
        bot_username = tg_bot.get("result", {}).get("username", "")

    return {
        "telegram": {
            "configured": tg_channel.is_configured(),
            "webhook_url": webhook_url,
            "webhook_active": webhook_active,
            "bot_username": bot_username,
        },
        "twilio_sms": {
            "configured": tw_channel.is_configured() and bool(tw_channel.TWILIO_PHONE_NUMBER),
        },
        "twilio_whatsapp": {
            "configured": tw_channel.is_configured() and bool(tw_channel.TWILIO_WHATSAPP_NUMBER),
        },
        "web": {"configured": True},
    }
