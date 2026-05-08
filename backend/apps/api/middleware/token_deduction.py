"""Deprecated token deduction middleware.

Operating Reserve is no longer charged by generic endpoint middleware. Reserve
is debited only by explicit billing-aware execution routes after successful
governed work, using the public pricing ladder.
"""

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


class TokenDeductionMiddleware(BaseHTTPMiddleware):
    """Compatibility shim that never mutates wallet state."""

    async def dispatch(self, request: Request, call_next):
        return await call_next(request)
