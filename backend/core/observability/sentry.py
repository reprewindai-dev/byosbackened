"""Sentry initialization for production error monitoring and tracing."""
from __future__ import annotations

import logging
from typing import Any

from core.config import get_settings

logger = logging.getLogger(__name__)

_INITIALIZED = False


def configure_sentry() -> bool:
    """Initialize Sentry once, using runtime env configuration only."""
    global _INITIALIZED
    if _INITIALIZED:
        return True

    settings = get_settings()
    if not settings.sentry_dsn:
        return False

    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration
    except Exception:
        logger.exception("sentry_sdk_import_failed")
        return False

    kwargs: dict[str, Any] = {
        "dsn": settings.sentry_dsn,
        "environment": settings.sentry_environment or settings.environment,
        "release": settings.sentry_release or settings.app_version,
        "send_default_pii": settings.sentry_send_default_pii,
        "traces_sample_rate": settings.sentry_traces_sample_rate,
        "profile_session_sample_rate": settings.sentry_profile_session_sample_rate,
        "enable_logs": settings.sentry_enable_logs,
        "integrations": [
            FastApiIntegration(),
            StarletteIntegration(),
            SqlalchemyIntegration(),
            LoggingIntegration(level=logging.INFO, event_level=logging.ERROR),
        ],
    }

    try:
        sentry_sdk.init(**kwargs)
    except TypeError:
        # Older SDK builds may not support the newest logging/profiling keyword names.
        # Keep error monitoring/tracing alive instead of failing application startup.
        kwargs.pop("enable_logs", None)
        kwargs.pop("profile_session_sample_rate", None)
        sentry_sdk.init(**kwargs)

    _INITIALIZED = True
    logger.info("sentry_initialized")
    return True
