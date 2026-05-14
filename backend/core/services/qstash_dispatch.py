"""QStash dispatch and receiver verification for durable UACP jobs."""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime
from typing import Any

import httpx

from core.config import get_settings

logger = logging.getLogger(__name__)


def _settings() -> Any:
    return get_settings()


def configured() -> bool:
    settings = _settings()
    return bool(settings.qstash_token and settings.qstash_callback_base_url)


def receiver_configured() -> bool:
    settings = _settings()
    return bool(settings.qstash_current_signing_key and settings.qstash_next_signing_key)


def _client() -> Any | None:
    settings = _settings()
    if not settings.qstash_token:
        return None
    try:
        from qstash import QStash

        return QStash(settings.qstash_token)
    except Exception:
        try:
            from qstash.client import QStash

            return QStash(settings.qstash_url, settings.qstash_token)
        except Exception:
            logger.warning("qstash_sdk_missing")
            return None


def _receiver() -> Any | None:
    settings = _settings()
    if not receiver_configured():
        return None
    try:
        from qstash import Receiver
    except Exception:
        logger.warning("qstash_receiver_sdk_missing")
        return None
    return Receiver(
        current_signing_key=settings.qstash_current_signing_key,
        next_signing_key=settings.qstash_next_signing_key,
    )


def job_url(path: str = "/api/v1/webhooks/qstash/uacp-job") -> str:
    settings = _settings()
    return f"{settings.qstash_callback_base_url.rstrip('/')}/{path.lstrip('/')}"


def workflow_url(path: str = "/api/v1/workflows/uacp-maintenance") -> str:
    settings = _settings()
    if settings.upstash_workflow_url:
        return settings.upstash_workflow_url
    return f"{settings.qstash_callback_base_url.rstrip('/')}/{path.lstrip('/')}"


def _message_id(response: Any) -> str | None:
    if isinstance(response, list):
        return _message_id(response[0]) if response else None
    if isinstance(response, dict):
        return response.get("message_id") or response.get("messageId")
    return getattr(response, "message_id", None) or getattr(response, "messageId", None)


def dispatch_uacp_job(
    *,
    job_type: str,
    payload: dict[str, Any],
    delay: str | None = None,
    retries: int = 3,
) -> dict[str, Any]:
    """Publish a durable UACP job to QStash."""
    client = _client()
    if client is None or not configured():
        return {
            "queued": False,
            "provider": "local-fallback",
            "reason": "QSTASH_TOKEN and QSTASH_CALLBACK_BASE_URL must be configured.",
        }

    body = {
        "job_type": job_type,
        "payload": payload,
        "dispatched_at": datetime.utcnow().isoformat() + "Z",
        "frame_hash": hashlib.sha256(
            json.dumps({"job_type": job_type, "payload": payload}, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest(),
    }
    try:
        if hasattr(client, "message") and hasattr(client.message, "publish_json"):
            response = client.message.publish_json(
                url=job_url(),
                body=body,
                headers={
                    "X-Veklom-Job-Type": job_type,
                    "X-Veklom-Frame-Hash": body["frame_hash"],
                },
                delay=delay,
                retries=retries,
                content_based_deduplication=True,
            )
        else:
            response = client.publish(
                url=job_url(),
                body=body,
                headers={
                    "Content-Type": "application/json",
                    "X-Veklom-Job-Type": job_type,
                    "X-Veklom-Frame-Hash": body["frame_hash"],
                },
                delay=delay,
                retries=retries,
            )
    except Exception as exc:
        logger.warning("qstash_dispatch_failed", exc_info=True)
        return {
            "queued": False,
            "provider": "qstash",
            "reason": f"QStash dispatch failed: {type(exc).__name__}",
        }

    return {
        "queued": True,
        "provider": "qstash",
        "message_id": _message_id(response),
        "target_url": job_url(),
        "job_type": job_type,
        "frame_hash": body["frame_hash"],
    }


def trigger_uacp_workflow(
    *,
    payload: dict[str, Any],
    workflow_target_url: str | None = None,
) -> dict[str, Any]:
    """Trigger the Upstash Workflow HTTP endpoint through QStash."""
    settings = _settings()
    if not settings.qstash_token:
        return {
            "triggered": False,
            "provider": "local-fallback",
            "reason": "QSTASH_TOKEN must be configured.",
        }
    target = workflow_target_url or workflow_url()
    if not target:
        return {
            "triggered": False,
            "provider": "local-fallback",
            "reason": "QSTASH_CALLBACK_BASE_URL or UPSTASH_WORKFLOW_URL must be configured.",
        }
    trigger_url = f"{settings.qstash_url.rstrip('/')}/v2/trigger/{target}"
    try:
        response = httpx.post(
            trigger_url,
            headers={
                "Authorization": f"Bearer {settings.qstash_token}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=10,
        )
        response.raise_for_status()
    except Exception as exc:
        logger.warning("qstash_workflow_trigger_failed", exc_info=True)
        return {
            "triggered": False,
            "provider": "qstash",
            "reason": f"QStash workflow trigger failed: {type(exc).__name__}",
            "target_url": target,
        }

    try:
        body = response.json()
    except ValueError:
        body = {"raw": response.text[:500]}

    return {
        "triggered": True,
        "provider": "qstash",
        "target_url": target,
        "status_code": response.status_code,
        "response": body,
    }


def verify_qstash_signature(*, body: bytes, signature: str, url: str) -> bool:
    """Verify an inbound QStash delivery with the official SDK Receiver."""
    receiver = _receiver()
    if receiver is None:
        return False
    try:
        receiver.verify(body=body, signature=signature, url=url)
        return True
    except Exception:
        logger.warning("qstash_signature_verification_failed", exc_info=True)
        return False
