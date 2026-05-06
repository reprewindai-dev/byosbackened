"""Resend webhook receiver."""
from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request

try:
    from svix.webhooks import Webhook, WebhookVerificationError
except ImportError:  # optional in local/test environments
    Webhook = None

    class WebhookVerificationError(Exception):
        pass

from core.config import get_settings
from core.redis_pool import get_redis
from herald.resend_sequences import suppress_email


logger = logging.getLogger(__name__)
router = APIRouter(tags=["resend-webhooks"])
settings = get_settings()

_DEDUP_TTL_SECONDS = 7 * 24 * 60 * 60


def _store_once(event_id: str) -> bool:
    """Return False for duplicate deliveries."""
    try:
        redis = get_redis()
        key = f"resend:webhook:{event_id}"
        return bool(redis.set(key, "1", nx=True, ex=_DEDUP_TTL_SECONDS))
    except Exception:
        # Fail open if Redis is unavailable; logging still records the event.
        return True


@router.post("/webhooks/resend", include_in_schema=False)
async def resend_webhook(request: Request) -> dict[str, Any]:
    """Receive Resend webhook events for email delivery/inbound state."""
    payload = await request.body()
    if not payload:
        raise HTTPException(status_code=400, detail="Empty webhook payload")

    event: dict[str, Any]
    if settings.resend_webhook_secret:
        if Webhook is None:
            raise HTTPException(status_code=503, detail="Resend signature verification dependency unavailable")
        headers = {
            "svix-id": request.headers.get("svix-id", ""),
            "svix-timestamp": request.headers.get("svix-timestamp", ""),
            "svix-signature": request.headers.get("svix-signature", ""),
        }
        if not all(headers.values()):
            raise HTTPException(status_code=400, detail="Missing Resend webhook signature headers")
        try:
            event = Webhook(settings.resend_webhook_secret).verify(payload, headers)
        except WebhookVerificationError as exc:
            raise HTTPException(status_code=400, detail="Invalid Resend webhook signature") from exc
    else:
        try:
            event = json.loads(payload.decode("utf-8"))
        except Exception as exc:
            raise HTTPException(status_code=400, detail="Invalid webhook payload") from exc
        logger.warning("Resend webhook accepted without signature verification because RESEND_WEBHOOK_SECRET is not configured")

    event_id = str(request.headers.get("svix-id") or event.get("id") or "")
    if event_id and not _store_once(event_id):
        return {"ok": True, "duplicate": True}

    event_type = str(event.get("type") or "unknown")
    data = event.get("data") or {}
    contact_data = data.get("contact") if isinstance(data.get("contact"), dict) else {}
    email = (
        data.get("email")
        or data.get("to")
        or data.get("recipient")
        or contact_data.get("email")
    )
    if isinstance(email, list):
        email = email[0] if email else ""
    if event_type in {"contact.unsubscribed", "email.bounced", "email.complained"}:
        suppress_email(str(email or ""), event_type)
    logger.info(
        "resend_webhook_received",
        extra={
            "event_type": event_type,
            "svix_id": event_id,
            "email_id": data.get("email_id"),
            "subject": data.get("subject"),
            "from": data.get("from"),
            "to": data.get("to"),
            "suppressed_email": email if event_type in {"contact.unsubscribed", "email.bounced", "email.complained"} else None,
        },
    )

    # Current behavior is observability-first:
    # accept and record delivery/inbound state for operational debugging.
    return {
        "ok": True,
        "type": event_type,
        "received": True,
    }
