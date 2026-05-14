"""Status update subscriber delivery."""
from __future__ import annotations

from datetime import datetime
import logging
from typing import Any

import httpx
from sqlalchemy.orm import Session

from core.notifications.emailer import send_email
from core.security.encryption import decrypt_field
from db.models import StatusSubscription


logger = logging.getLogger(__name__)


def _status_payload(
    *,
    event_type: str,
    title: str,
    description: str,
    severity: str,
    status: str,
    url: str,
) -> dict[str, Any]:
    return {
        "event_type": event_type,
        "title": title,
        "description": description,
        "severity": severity,
        "status": status,
        "url": url,
        "timestamp": datetime.utcnow().isoformat(),
    }


async def _send_webhook(url: str, payload: dict[str, Any]) -> None:
    async with httpx.AsyncClient(timeout=8.0) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()


async def _send_slack(url: str, payload: dict[str, Any]) -> None:
    text = f"Veklom status update: {payload['title']}"
    slack_payload = {
        "text": text,
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"*{payload['title']}*\n"
                        f"Status: `{payload['status']}` - Severity: `{payload['severity']}`\n"
                        f"{payload['description']}\n"
                        f"<{payload['url']}|Open status page>"
                    ),
                },
            }
        ],
    }
    await _send_webhook(url, slack_payload)


async def _send_email(target: str, payload: dict[str, Any]) -> None:
    await send_email(
        to_email=target,
        subject=f"Veklom status update: {payload['title']}",
        text_body=(
            f"{payload['title']}\n\n"
            f"Status: {payload['status']}\n"
            f"Severity: {payload['severity']}\n\n"
            f"{payload['description']}\n\n"
            f"Status page: {payload['url']}\n"
        ),
        html_body=(
            f"<p><strong>{payload['title']}</strong></p>"
            f"<p>Status: <code>{payload['status']}</code><br />"
            f"Severity: <code>{payload['severity']}</code></p>"
            f"<p>{payload['description']}</p>"
            f"<p><a href=\"{payload['url']}\">Open Veklom status page</a></p>"
        ),
    )


async def notify_status_subscribers(
    db: Session,
    *,
    event_type: str,
    title: str,
    description: str,
    severity: str,
    status: str,
    url: str = "https://veklom.com/status",
) -> dict[str, int]:
    """Deliver a status update to active public status subscribers."""
    payload = _status_payload(
        event_type=event_type,
        title=title,
        description=description,
        severity=severity,
        status=status,
        url=url,
    )
    subscribers = (
        db.query(StatusSubscription)
        .filter(StatusSubscription.status == "active")
        .all()
    )
    sent = 0
    failed = 0

    for subscriber in subscribers:
        try:
            target = decrypt_field(subscriber.target_encrypted)
            if subscriber.channel == "email":
                await _send_email(target, payload)
            elif subscriber.channel == "slack":
                await _send_slack(target, payload)
            elif subscriber.channel == "webhook":
                await _send_webhook(target, payload)
            else:
                continue
            subscriber.last_delivery_status = "delivered"
            subscriber.last_delivery_at = datetime.utcnow()
            sent += 1
        except Exception as exc:
            failed += 1
            subscriber.failure_count = int(subscriber.failure_count or 0) + 1
            subscriber.last_delivery_status = f"failed:{type(exc).__name__}"
            subscriber.last_delivery_at = datetime.utcnow()
            logger.warning(
                "status_update_delivery_failed",
                extra={
                    "subscription_id": subscriber.id,
                    "channel": subscriber.channel,
                    "error": str(exc),
                },
            )

    db.commit()
    return {"subscribers": len(subscribers), "sent": sent, "failed": failed}
