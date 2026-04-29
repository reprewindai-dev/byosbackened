"""Trial license issuance and onboarding helpers."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
from fastapi import HTTPException
from sqlalchemy.orm import Session

from core.config import get_settings
from core.notifications.emailer import send_trial_welcome_email
from db.models import LicenseTier, Workspace

logger = logging.getLogger(__name__)
settings = get_settings()

TRIAL_DURATION_DAYS = 14
SELF_SERVE_TIERS = {"starter", "pro", "sovereign", "enterprise"}


@dataclass(slots=True)
class TrialLicensePayload:
    license_id: str
    license_key: str
    key_prefix: str
    workspace_id: str
    tier: str
    expires_at: datetime


def resolve_trial_tier(requested_tier: Optional[str]) -> LicenseTier:
    normalized = (requested_tier or "starter").strip().lower()
    if normalized not in SELF_SERVE_TIERS:
        normalized = "starter"
    return LicenseTier(normalized)


def build_trial_download_url(tier: str) -> str:
    version = (settings.buyer_download_version or settings.app_version).strip()
    filename = f"veklom-backend-{tier}-{version}.zip"
    base = (settings.buyer_download_base_url or "").strip().rstrip("/")
    if base:
        if base.endswith(".zip"):
            return base
        return f"{base}/{filename}"
    return f"https://veklom.com/downloads/{tier}/{filename}"


async def issue_trial_license(
    *,
    db: Session,
    workspace: Workspace,
    user_email: str,
    user_name: str,
    requested_tier: Optional[str],
) -> TrialLicensePayload:
    tier = resolve_trial_tier(requested_tier)
    expires_at = datetime.now(timezone.utc) + timedelta(days=TRIAL_DURATION_DAYS)
    issue_url = settings.license_issue_url.strip()
    if not issue_url:
        raise HTTPException(status_code=503, detail="License issuance endpoint not configured")

    payload = {
        "workspace_id": workspace.id,
        "tier": tier.value,
        "expires_at": expires_at.isoformat(),
        "metadata": {
            "workspace_name": workspace.name,
            "signup_email": user_email,
            "signup_name": user_name,
            "source": "trial_signup",
            "trial_days": TRIAL_DURATION_DAYS,
        },
    }
    headers = {"X-Admin-Token": settings.license_admin_token} if settings.license_admin_token else {}

    timeout = httpx.Timeout(8.0, connect=3.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(issue_url, json=payload, headers=headers)
    if response.status_code >= 400:
        raise HTTPException(
            status_code=502,
            detail=f"License issuance failed: {response.status_code}",
        )

    data = response.json()
    expires_value = data["expires_at"]
    if isinstance(expires_value, str):
        expires_dt = datetime.fromisoformat(expires_value.replace("Z", "+00:00"))
    else:
        expires_dt = expires_value

    license_payload = TrialLicensePayload(
        license_id=data["license_id"],
        license_key=data["license_key"],
        key_prefix=data.get("key_prefix") or data["license_key"][:12],
        workspace_id=data["workspace_id"],
        tier=data["tier"],
        expires_at=expires_dt,
    )

    workspace.license_key_id = license_payload.license_id
    workspace.license_key_prefix = license_payload.key_prefix
    workspace.license_tier = license_payload.tier
    workspace.license_issued_at = datetime.now(timezone.utc).replace(tzinfo=None)
    workspace.license_expires_at = license_payload.expires_at.replace(tzinfo=None)
    workspace.license_download_url = build_trial_download_url(license_payload.tier)
    db.flush()

    return license_payload


async def send_trial_welcome(
    *,
    workspace: Workspace,
    user_email: str,
    user_name: str,
    license_payload: TrialLicensePayload,
) -> None:
    download_url = build_trial_download_url(license_payload.tier)
    await send_trial_welcome_email(
        to_email=user_email,
        workspace_name=user_name or workspace.name,
        tier=license_payload.tier,
        license_key=license_payload.license_key,
        download_url=download_url,
        expires_at_iso=license_payload.expires_at.astimezone(timezone.utc).isoformat(),
    )

