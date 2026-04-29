"""Runtime middleware for enforcing remote license state."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from core.config import get_settings
from license.validator import (
    LicenseValidationResult,
    cache_license_result,
    enforce_license_on_startup,
    get_cached_license_result,
    verify_license_once,
)

logger = logging.getLogger(__name__)

LICENSE_EXEMPT_PATHS = {
    "/health",
    "/status",
    "/",
    "/api/v1/subscriptions/plans",
    "/api/v1/subscriptions/webhook",
    "/api/v1/auth/login",
    "/api/v1/auth/register",
}


async def bootstrap_license_check() -> LicenseValidationResult:
    """Run the startup license check and cache the result."""
    result = await enforce_license_on_startup()
    cache_license_result(result)
    return result


class LicenseGateMiddleware(BaseHTTPMiddleware):
    """Fail closed when the remote license becomes invalid."""

    def __init__(self, app, refresh_seconds: Optional[int] = None):
        super().__init__(app)
        settings = get_settings()
        self.refresh_seconds = refresh_seconds or int(settings.license_revalidation_seconds or 900)
        self._last_check_at: Optional[datetime] = None

    async def _refresh_if_needed(self) -> LicenseValidationResult:
        current = get_cached_license_result()
        now = datetime.now(timezone.utc)
        if current and self._last_check_at:
            age = (now - self._last_check_at).total_seconds()
            if age < self.refresh_seconds:
                return current
        result = await verify_license_once()
        self._last_check_at = now
        return result

    async def dispatch(self, request: Request, call_next):
        settings = get_settings()
        if not settings.license_enforcement_enabled:
            return await call_next(request)

        if request.url.path in LICENSE_EXEMPT_PATHS:
            return await call_next(request)

        result = await self._refresh_if_needed()
        if result.valid:
            request.state.license_status = result.status
            request.state.license_tier = result.tier
            response = await call_next(request)
            response.headers["X-License-Status"] = result.status
            if result.grace_until and result.status == "grace":
                response.headers["X-License-Grace-Until"] = result.grace_until.isoformat()
            return response

        if result.reason == "payment_failed" and result.grace_until:
            if datetime.now(timezone.utc) < result.grace_until:
                request.state.license_status = "grace"
                request.state.license_tier = result.tier
                response = await call_next(request)
                response.headers["X-License-Status"] = "grace"
                response.headers["X-License-Grace-Until"] = result.grace_until.isoformat()
                return response

        logger.error("Blocking request due to invalid license: %s", result.reason)
        return JSONResponse(
            status_code=503,
            content={
                "detail": "License validation failed",
                "reason": result.reason,
                "status": result.status,
            },
        )
