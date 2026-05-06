"""Resend-backed HERALD signup sequences.

HERALD is intentionally best-effort. Missing Resend configuration, transient
network failures, or scheduler downtime must never block signup, auth, or trial
license issuance.
"""
from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Literal

import httpx

from core.config import get_settings
from core.redis_pool import get_redis

logger = logging.getLogger(__name__)
settings = get_settings()

Audience = Literal["vendor", "regulated"]
_SCHEDULE_ZSET = "herald:scheduled"
_SCHEDULE_PAYLOAD_PREFIX = "herald:scheduled:"
_SUPPRESSION_SET = "herald:suppressed"


@dataclass(frozen=True)
class HeraldContact:
    email: str
    first_name: str
    workspace_id: str
    user_id: str
    signup_type: str = "general"


@dataclass(frozen=True)
class HeraldMessage:
    sequence: str
    step: int
    delay_days: int
    subject: str
    text: str
    html: str
    from_email: str
    audience_id: str


def _configured() -> bool:
    return bool(settings.resend_api_key)


def _audience_for_signup(signup_type: str) -> Audience:
    normalized = (signup_type or "").strip().lower()
    if normalized in {"vendor", "marketplace_vendor", "supplier", "partner"}:
        return "vendor"
    if normalized in {"regulated", "buyer", "bank", "hospital", "insurance", "government"}:
        return "regulated"
    return "regulated"


def _display_name(contact: HeraldContact) -> str:
    return (contact.first_name or contact.email.split("@")[0]).strip()


def _vendor_messages(contact: HeraldContact) -> list[HeraldMessage]:
    name = _display_name(contact)
    from_email = settings.resend_from_vendor or settings.mail_from or "Veklom Marketplace <noreply@veklom.com>"
    audience_id = settings.resend_vendor_audience_id
    return [
        HeraldMessage(
            sequence="vendor",
            step=1,
            delay_days=0,
            subject="Your Veklom marketplace intake is open",
            text=(
                f"Hi {name},\n\n"
                "Veklom Marketplace is built for vendors that need regulated buyers to trust what they install. "
                "Your next step is to prepare the product profile, security notes, audit/logging explanation, "
                "and deployment details we can validate before listing.\n\n"
                "This is guidance and verification support, not a legal certification.\n"
            ),
            html=(
                f"<p>Hi {name},</p>"
                "<p>Veklom Marketplace is built for vendors that need regulated buyers to trust what they install.</p>"
                "<p>Prepare the product profile, security notes, audit/logging explanation, and deployment details we can validate before listing.</p>"
                "<p><strong>Note:</strong> this is guidance and verification support, not a legal certification.</p>"
            ),
            from_email=from_email,
            audience_id=audience_id,
        ),
        HeraldMessage(
            sequence="vendor",
            step=2,
            delay_days=3,
            subject="What regulated buyers need before they trust a marketplace listing",
            text=(
                "Regulated buyers look for deployment boundaries, access controls, data handling, logging, "
                "versioning, and a clear rollback story. Veklom packages that evidence into a buyer-facing "
                "listing instead of leaving every vendor to answer it from scratch.\n"
            ),
            html=(
                "<p>Regulated buyers look for deployment boundaries, access controls, data handling, logging, versioning, and rollback.</p>"
                "<p>Veklom packages that evidence into a buyer-facing listing instead of leaving every vendor to answer it from scratch.</p>"
            ),
            from_email=from_email,
            audience_id=audience_id,
        ),
        HeraldMessage(
            sequence="vendor",
            step=3,
            delay_days=7,
            subject="Ready for Veklom Verified guidance review?",
            text=(
                "The Veklom Verified guidance review checks whether the listing evidence is complete enough for "
                "a serious regulated buyer conversation. It does not replace legal, SOC 2, HIPAA, or regulatory certification.\n"
            ),
            html=(
                "<p>The Veklom Verified guidance review checks whether the listing evidence is complete enough for a serious regulated buyer conversation.</p>"
                "<p>It does not replace legal, SOC 2, HIPAA, or regulatory certification.</p>"
            ),
            from_email=from_email,
            audience_id=audience_id,
        ),
    ]


def _regulated_messages(contact: HeraldContact) -> list[HeraldMessage]:
    name = _display_name(contact)
    from_email = settings.resend_from_compliance or settings.mail_from or "Veklom Compliance <compliance@veklom.com>"
    audience_id = settings.resend_regulated_audience_id
    return [
        HeraldMessage(
            sequence="regulated",
            step=1,
            delay_days=0,
            subject="Your Veklom free evaluation is ready",
            text=(
                f"Hi {name},\n\n"
                "Your Veklom evaluation is ready. Veklom controls AI execution through policy, budget checks, "
                "routing decisions, and audit traces so regulated teams can prove what happened from request to result.\n\n"
                "We do not grant an unlimited token pool in the trial. Evaluation access is governed by the backend entitlement and usage controls.\n"
            ),
            html=(
                f"<p>Hi {name},</p>"
                "<p>Your Veklom evaluation is ready. Veklom controls AI execution through policy, budget checks, routing decisions, and audit traces.</p>"
                "<p>Evaluation access is governed by backend entitlement and usage controls, not an unlimited token pool.</p>"
            ),
            from_email=from_email,
            audience_id=audience_id,
        ),
        HeraldMessage(
            sequence="regulated",
            step=2,
            delay_days=4,
            subject="The proof buyers should ask from every AI system",
            text=(
                "For each governed execution, ask for the normalized input, decision reason, cost control, trace, and audit proof. "
                "That is the operating difference between a chat box and a controlled AI system.\n"
            ),
            html=(
                "<p>For each governed execution, ask for the normalized input, decision reason, cost control, trace, and audit proof.</p>"
                "<p>That is the difference between a chat box and a controlled AI system.</p>"
            ),
            from_email=from_email,
            audience_id=audience_id,
        ),
        HeraldMessage(
            sequence="regulated",
            step=3,
            delay_days=9,
            subject="When to move Veklom from evaluation to production",
            text=(
                "Move from evaluation to production when the workspace has approved models, API keys, budget caps, route policy, "
                "audit exports, and the operational owner who receives alerts.\n"
            ),
            html=(
                "<p>Move from evaluation to production when the workspace has approved models, API keys, budget caps, route policy, audit exports, and an operational alert owner.</p>"
            ),
            from_email=from_email,
            audience_id=audience_id,
        ),
    ]


def build_sequence(contact: HeraldContact) -> list[HeraldMessage]:
    audience = _audience_for_signup(contact.signup_type)
    return _vendor_messages(contact) if audience == "vendor" else _regulated_messages(contact)


async def _post_resend(path: str, payload: dict) -> None:
    if not _configured():
        logger.info("HERALD skipped Resend call because RESEND_API_KEY is not configured")
        return
    headers = {
        "Authorization": f"Bearer {settings.resend_api_key}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(f"https://api.resend.com{path}", headers=headers, json=payload)
        response.raise_for_status()


async def upsert_contact(contact: HeraldContact, audience_id: str) -> None:
    if not audience_id:
        return
    await _post_resend(
        f"/audiences/{audience_id}/contacts",
        {
            "email": contact.email,
            "first_name": _display_name(contact),
            "unsubscribed": False,
        },
    )


async def send_message(contact: HeraldContact, message: HeraldMessage) -> None:
    if is_suppressed(contact.email):
        logger.info("HERALD skipped suppressed contact %s", contact.email)
        return
    await upsert_contact(contact, message.audience_id)
    await _post_resend(
        "/emails",
        {
            "from": message.from_email,
            "to": [contact.email],
            "subject": message.subject,
            "text": message.text,
            "html": message.html,
            "tags": [
                {"name": "system", "value": "herald"},
                {"name": "sequence", "value": message.sequence},
                {"name": "step", "value": str(message.step)},
                {"name": "workspace_id", "value": contact.workspace_id},
            ],
        },
    )


def _schedule_key(contact: HeraldContact, message: HeraldMessage) -> str:
    return f"{contact.workspace_id}:{contact.user_id}:{message.sequence}:{message.step}"


def _schedule_message(contact: HeraldContact, message: HeraldMessage) -> None:
    try:
        redis = get_redis()
    except Exception as exc:
        logger.warning("HERALD scheduler unavailable; Redis not reachable: %s", exc)
        return
    due_at = datetime.now(timezone.utc) + timedelta(days=message.delay_days)
    key = _schedule_key(contact, message)
    payload = {
        "contact": contact.__dict__,
        "message": message.__dict__,
        "due_at": due_at.isoformat(),
    }
    redis.set(f"{_SCHEDULE_PAYLOAD_PREFIX}{key}", json.dumps(payload), ex=30 * 24 * 60 * 60)
    redis.zadd(_SCHEDULE_ZSET, {key: due_at.timestamp()})


async def enroll_signup(contact: HeraldContact) -> None:
    sequence = build_sequence(contact)
    if not sequence:
        return
    for message in sequence:
        if message.delay_days <= 0:
            try:
                await send_message(contact, message)
            except Exception as exc:
                logger.warning("HERALD immediate send failed for %s: %s", contact.email, exc)
        else:
            _schedule_message(contact, message)


async def process_due_messages(limit: int = 100) -> int:
    try:
        redis = get_redis()
    except Exception as exc:
        logger.warning("HERALD due-message processing skipped; Redis unavailable: %s", exc)
        return 0

    now_score = datetime.now(timezone.utc).timestamp()
    keys = redis.zrangebyscore(_SCHEDULE_ZSET, min=0, max=now_score, start=0, num=limit)
    processed = 0
    for key in keys:
        payload_key = f"{_SCHEDULE_PAYLOAD_PREFIX}{key}"
        raw_payload = redis.get(payload_key)
        redis.zrem(_SCHEDULE_ZSET, key)
        redis.delete(payload_key)
        if not raw_payload:
            continue
        payload = json.loads(raw_payload)
        contact = HeraldContact(**payload["contact"])
        message = HeraldMessage(**payload["message"])
        try:
            await send_message(contact, message)
            processed += 1
        except Exception as exc:
            logger.warning("HERALD scheduled send failed for %s: %s", contact.email, exc)
    return processed


def suppress_email(email: str, reason: str) -> None:
    normalized = (email or "").strip().lower()
    if not normalized:
        return
    try:
        redis = get_redis()
        redis.sadd(_SUPPRESSION_SET, normalized)
        redis.set(f"herald:suppressed:{normalized}", reason, ex=365 * 24 * 60 * 60)
    except Exception as exc:
        logger.warning("HERALD suppression could not be stored for %s: %s", normalized, exc)


def is_suppressed(email: str) -> bool:
    normalized = (email or "").strip().lower()
    if not normalized:
        return True
    try:
        return bool(get_redis().sismember(_SUPPRESSION_SET, normalized))
    except Exception:
        return False


def enqueue_signup(contact: HeraldContact) -> None:
    try:
        asyncio.get_running_loop().create_task(enroll_signup(contact))
    except RuntimeError:
        asyncio.run(enroll_signup(contact))
