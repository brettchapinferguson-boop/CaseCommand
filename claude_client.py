"""
CaseCommand — Claude API Client
================================
Shared async client for the Anthropic API with:
- Connection pooling (one httpx.AsyncClient for the process)
- Retry with exponential backoff on 429/529
- Tool use support for agentic loops
- Prompt caching (cache_control on system prompt) to cut cost/latency
  for the always-on paralegal agent
"""

import os
import asyncio
import logging
from typing import Dict, List, Optional

import httpx

logger = logging.getLogger("casecommand.claude")

API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
# Opus 4.8 is Anthropic's recommended default for agentic applications
# (long-horizon tool use, 1M context). The background worker runs Sonnet 5
# by default — near-Opus agentic quality at the high-volume price tier.
MODEL = os.environ.get("CLAUDE_MODEL", "claude-opus-4-8")
WORKER_MODEL = os.environ.get("WORKER_MODEL", "claude-sonnet-5")

# Opus 4.7+, Sonnet 5, and Fable 5 reject temperature/top_p/top_k with 400
# errors (they use adaptive thinking instead). Only send temperature to
# models that still accept it.
_NO_TEMPERATURE_MODELS = ("claude-opus-4-7", "claude-opus-4-8",
                          "claude-sonnet-5", "claude-fable-5", "claude-mythos-5")


def _supports_temperature(model: str) -> bool:
    return not any(model.startswith(m) for m in _NO_TEMPERATURE_MODELS)

API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"

_http_client: Optional[httpx.AsyncClient] = None


def get_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(timeout=180)
    return _http_client


async def close_http_client():
    global _http_client
    if _http_client and not _http_client.is_closed:
        await _http_client.aclose()
        _http_client = None


def _headers() -> Dict:
    return {
        "Content-Type": "application/json",
        "x-api-key": API_KEY,
        "anthropic-version": ANTHROPIC_VERSION,
    }


def _cacheable_system(system: str) -> List[Dict]:
    """Wrap the system prompt in a cache_control block. The case-portfolio
    system prompt is large and mostly stable within a 5-minute window, so
    caching it cuts input cost substantially for multi-turn/agentic use."""
    return [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]


async def call_claude_raw(
    system: str,
    messages: List[Dict],
    model: Optional[str] = None,
    max_tokens: int = 4096,
    temperature: float = 0.3,
    tools: Optional[List[Dict]] = None,
) -> Dict:
    """Low-level call. Returns the full API response envelope:
    {success, content (block list), stop_reason, usage, error}
    """
    if not API_KEY:
        logger.error("Claude API call attempted without API key")
        return {
            "success": False,
            "content": [],
            "stop_reason": None,
            "usage": {},
            "error": "No API key configured. Add ANTHROPIC_API_KEY to .env",
        }

    use_model = model or MODEL
    payload = {
        "model": use_model,
        "max_tokens": max_tokens,
        "system": _cacheable_system(system),
        "messages": messages,
    }
    if temperature is not None and _supports_temperature(use_model):
        payload["temperature"] = temperature
    if tools:
        payload["tools"] = tools

    client = get_http_client()

    for attempt in range(3):
        try:
            resp = await client.post(API_URL, headers=_headers(), json=payload)
            if resp.status_code == 200:
                data = resp.json()
                usage = data.get("usage", {})
                logger.info(
                    "Claude API ok: in=%d out=%d cache_read=%d stop=%s",
                    usage.get("input_tokens", 0),
                    usage.get("output_tokens", 0),
                    usage.get("cache_read_input_tokens", 0),
                    data.get("stop_reason"),
                )
                return {
                    "success": True,
                    "content": data.get("content", []),
                    "stop_reason": data.get("stop_reason"),
                    "usage": usage,
                    "error": None,
                }
            if resp.status_code in (429, 529):
                wait = (2**attempt) * 2
                logger.warning(
                    "Claude API %d, retrying in %ds (attempt %d/3)",
                    resp.status_code, wait, attempt + 1,
                )
                await asyncio.sleep(wait)
                continue
            logger.error("Claude API error %d: %s", resp.status_code, resp.text[:300])
            return {
                "success": False, "content": [], "stop_reason": None, "usage": {},
                "error": f"AI service error (status {resp.status_code})",
            }
        except httpx.TimeoutException:
            logger.warning("Claude API timeout (attempt %d/3)", attempt + 1)
            if attempt < 2:
                await asyncio.sleep(1)
                continue
            return {"success": False, "content": [], "stop_reason": None,
                    "usage": {}, "error": "AI service timeout"}
        except Exception:
            logger.exception("Claude API unexpected error (attempt %d/3)", attempt + 1)
            if attempt < 2:
                await asyncio.sleep(1)
                continue
            return {"success": False, "content": [], "stop_reason": None,
                    "usage": {}, "error": "AI service unavailable"}

    return {"success": False, "content": [], "stop_reason": None,
            "usage": {}, "error": "Max retries exceeded"}


async def call_claude(
    system: str,
    messages: List[Dict],
    max_tokens: int = 4096,
    temperature: float = 0.3,
    model: Optional[str] = None,
) -> Dict:
    """Text-only convenience wrapper (back-compat with existing endpoints).
    Returns {success, text, usage, error}."""
    result = await call_claude_raw(
        system, messages[-20:], model=model,
        max_tokens=max_tokens, temperature=temperature,
    )
    if not result["success"]:
        return {"success": False, "text": "", "error": result["error"]}
    text = "".join(
        b.get("text", "") for b in result["content"] if b.get("type") == "text"
    )
    return {"success": True, "text": text, "usage": result["usage"]}
