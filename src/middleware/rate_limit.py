"""
CaseCommand — Rate Limiting Middleware

Per-user rate limiting using SlowAPI.
Prevents abuse and protects Anthropic API budget.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request
from fastapi.responses import JSONResponse


def _get_user_key(request: Request) -> str:
    """
    Rate limit key: use authenticated user ID if available,
    otherwise fall back to IP address.
    """
    # After auth middleware runs, user may be attached to request state
    user = getattr(request.state, "user", None)
    if user and hasattr(user, "user_id"):
        return f"user:{user.user_id}"
    return get_remote_address(request)


limiter = Limiter(key_func=_get_user_key)


async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={
            "detail": "Rate limit exceeded. Please slow down.",
            "retry_after": str(exc.detail),
        },
    )
