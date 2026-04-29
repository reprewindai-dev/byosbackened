"""Stripe webhook bridge for license revocation."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import stripe
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from core.config import get_settings
from db.models import LicenseKey
from db.session import get_db

settings = get_settings()
router = APIRouter(tags=["license-webhook"])


def _parse_metadata(data: Dict[str, Any]) -> Dict[str, Any]:
    metadata = data.get("metadata") or {}
    if isinstance(metadata, dict):
        return metadata
    return {}


def _select_license_query(
    db: Session,
    customer_id: Optional[str],
    subscription_id: Optional[str],
    workspace_id: Optional[str],
):
    query = db.query(LicenseKey)
    filters = []
    if customer_id:
        filters.append(LicenseKey.stripe_customer_id == customer_id)
    if subscription_id:
        filters.append(LicenseKey.stripe_subscription_id == subscription_id)
    if workspace_id:
        filters.append(LicenseKey.workspace_id == workspace_id)
    if not filters:
        return query.filter(False)
    from sqlalchemy import or_

    return query.filter(or_(*filters))


def _deactivate_licenses(
    db: Session,
    *,
    customer_id: Optional[str] = None,
    subscription_id: Optional[str] = None,
    workspace_id: Optional[str] = None,
    reason: str,
    grace_hours: int = 72,
) -> int:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    grace_until = now + timedelta(hours=grace_hours) if reason == "payment_failed" else None
    licenses = _select_license_query(db, customer_id, subscription_id, workspace_id).all()
    count = 0
    for license_key in licenses:
        license_key.active = False
        license_key.revoked_reason = reason
        license_key.deactivated_at = now
        license_key.grace_until = grace_until
        license_key.updated_at = now
        count += 1
    db.commit()
    return count


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: Optional[str] = Header(None, alias="Stripe-Signature"),
    db: Session = Depends(get_db),
):
    """Process Stripe events that revoke or pause licenses."""
    if not settings.stripe_webhook_secret:
        raise HTTPException(status_code=503, detail="Stripe webhook is not configured")
    if not stripe_signature:
        raise HTTPException(status_code=400, detail="Missing Stripe-Signature header")

    body = await request.body()
    try:
        event = stripe.Webhook.construct_event(body, stripe_signature, settings.stripe_webhook_secret)
    except stripe.error.SignatureVerificationError as exc:
        raise HTTPException(status_code=400, detail="Invalid webhook signature") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid webhook payload") from exc

    event_type = event.get("type")
    data = event.get("data", {}).get("object", {}) or {}
    metadata = _parse_metadata(data)
    workspace_id = metadata.get("workspace_id")
    customer_id = data.get("customer") or metadata.get("stripe_customer_id")
    subscription_id = data.get("id") or metadata.get("stripe_subscription_id")

    if event_type in {"invoice.payment_failed", "payment_intent.payment_failed"}:
        count = _deactivate_licenses(
            db,
            customer_id=customer_id,
            subscription_id=subscription_id,
            workspace_id=workspace_id,
            reason="payment_failed",
            grace_hours=int(settings.license_grace_hours or 72),
        )
        return {"ok": True, "event": event_type, "licenses_updated": count}

    if event_type == "customer.subscription.deleted":
        count = _deactivate_licenses(
            db,
            customer_id=customer_id,
            subscription_id=subscription_id,
            workspace_id=workspace_id,
            reason="subscription_deleted",
            grace_hours=0,
        )
        return {"ok": True, "event": event_type, "licenses_updated": count}

    return {"ok": True, "event": event_type, "licenses_updated": 0}
