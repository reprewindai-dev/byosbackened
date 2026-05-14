"""Standalone license server for issuing, activating, verifying, and revoking keys."""
from __future__ import annotations

import hashlib
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.config import get_settings
from core.security.encryption import encrypt_field
from db.models import LicenseKey
from db.session import Base, engine, get_db
from license.tier import LicenseTier
from license.server_signing import build_license_payload, sign_license_payload
from license.stripe_webhook import router as stripe_webhook_router

settings = get_settings()
app = FastAPI(title="Veklom License Server", version=settings.app_version)
app.include_router(stripe_webhook_router, prefix="/stripe")
START_MONOTONIC = time.monotonic()
START_TIMESTAMP = datetime.now(timezone.utc)


class IssueRequest(BaseModel):
    workspace_id: str
    tier: LicenseTier
    expires_at: Optional[datetime] = None
    machine_fingerprint: Optional[str] = None
    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class IssueResponse(BaseModel):
    license_id: str
    license_key: str
    key_prefix: str
    workspace_id: str
    tier: str
    expires_at: datetime


class ActivateRequest(BaseModel):
    license_key: str
    machine_fingerprint: str


class VerifyRequest(BaseModel):
    license_key: str
    machine_fingerprint: str
    package_name: str = "veklom-backend"
    package_version: str = "0.1.0"


class DeactivateRequest(BaseModel):
    license_key: str
    reason: Optional[str] = "manual"


class VerifyResponse(BaseModel):
    valid: bool
    status: str
    reason: str
    workspace_id: Optional[str] = None
    tier: Optional[str] = None
    expires_at: Optional[datetime] = None
    grace_until: Optional[datetime] = None
    machine_fingerprint_bound: Optional[str] = None
    license_key_prefix: Optional[str] = None


def _admin_guard(x_admin_token: Optional[str]) -> None:
    if not settings.license_admin_token:
        raise HTTPException(status_code=503, detail="License admin token not configured")
    if x_admin_token != settings.license_admin_token:
        raise HTTPException(status_code=403, detail="Forbidden")


def _key_hash(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def _normalize_key(raw_key: str) -> str:
    key = (raw_key or "").strip()
    if not key:
        raise HTTPException(status_code=400, detail="license_key is required")
    return key


def _serialize_license(record: LicenseKey) -> VerifyResponse:
    return VerifyResponse(
        valid=bool(record.active),
        status="active" if record.active else "inactive",
        reason=record.revoked_reason or "",
        workspace_id=record.workspace_id,
        tier=record.tier.value,
        expires_at=record.expires_at,
        grace_until=record.grace_until,
        machine_fingerprint_bound=record.machine_fingerprint,
        license_key_prefix=record.key_prefix,
    )


@app.on_event("startup")
async def startup() -> None:
    import db.models  # noqa: F401

    Base.metadata.create_all(bind=engine)


@app.get("/status")
async def status_check() -> dict[str, str]:
    return {"status": "ok", "service": "license-server"}


@app.get("/health")
async def health_check() -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    return {
        "status": "ok",
        "server": "license-server",
        "uptime_seconds": round(time.monotonic() - START_MONOTONIC, 3),
        "started_at": START_TIMESTAMP.isoformat(),
        "timestamp": now.isoformat(),
    }


@app.post("/issue", response_model=IssueResponse, include_in_schema=False)
@app.post("/api/licenses/issue", response_model=IssueResponse)
async def issue_license(
    payload: IssueRequest,
    x_admin_token: Optional[str] = Header(None, alias="X-Admin-Token"),
    db: Session = Depends(get_db),
):
    _admin_guard(x_admin_token)

    raw_key = "vklm_" + secrets.token_urlsafe(40)
    expires_at = payload.expires_at or (datetime.now(timezone.utc) + timedelta(days=365))
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    record = LicenseKey(
        key_hash=_key_hash(raw_key),
        encrypted_key=encrypt_field(raw_key),
        key_prefix=raw_key[:12],
        workspace_id=payload.workspace_id,
        tier=payload.tier,
        machine_fingerprint=payload.machine_fingerprint,
        stripe_customer_id=payload.stripe_customer_id,
        stripe_subscription_id=payload.stripe_subscription_id,
        expires_at=expires_at.replace(tzinfo=None) if expires_at.tzinfo else expires_at,
        active=True,
        license_metadata=payload.metadata or {},
        created_at=now,
        updated_at=now,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return IssueResponse(
        license_id=record.id,
        license_key=raw_key,
        key_prefix=record.key_prefix,
        workspace_id=record.workspace_id,
        tier=record.tier.value,
        expires_at=record.expires_at,
    )


@app.post("/activate", response_model=VerifyResponse)
async def activate_license(payload: ActivateRequest, db: Session = Depends(get_db)):
    raw_key = _normalize_key(payload.license_key)
    record = db.query(LicenseKey).filter(LicenseKey.key_hash == _key_hash(raw_key)).first()
    if not record:
        raise HTTPException(status_code=404, detail="License not found")
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if record.expires_at and now > record.expires_at:
        raise HTTPException(status_code=403, detail="License expired")
    if record.machine_fingerprint and record.machine_fingerprint != payload.machine_fingerprint:
        raise HTTPException(status_code=403, detail="License already bound to a different machine")

    record.machine_fingerprint = payload.machine_fingerprint
    record.active = True
    record.revoked_reason = None
    record.activated_at = now
    record.deactivated_at = None
    record.updated_at = now
    db.commit()
    db.refresh(record)
    return _serialize_license(record)


def _signed_verify_envelope(record: LicenseKey, status: str, machine_fingerprint: str) -> dict[str, Any]:
    package_name = getattr(record, "_request_package_name", "veklom-backend")
    package_version = getattr(record, "_request_package_version", settings.app_version)
    payload = build_license_payload(
        license_id=record.id,
        workspace_id=record.workspace_id,
        tier=record.tier.value,
        features={"edge_control_layer": True, "v1_exec": True},
        machine_fingerprint=machine_fingerprint,
        package_name=package_name,
        package_version=package_version,
        status=status,
        expires_at=record.expires_at.replace(tzinfo=timezone.utc) if record.expires_at and record.expires_at.tzinfo is None else record.expires_at,
        grace_until=record.grace_until.replace(tzinfo=timezone.utc) if record.grace_until and record.grace_until.tzinfo is None else record.grace_until,
    )
    return sign_license_payload(payload)


@app.post("/verify", include_in_schema=False)
@app.post("/api/licenses/verify")
async def verify_license(payload: VerifyRequest, db: Session = Depends(get_db)):
    raw_key = _normalize_key(payload.license_key)
    record = db.query(LicenseKey).filter(LicenseKey.key_hash == _key_hash(raw_key)).first()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if not record:
        return {"valid": False, "status": "missing", "reason": "license_not_found"}

    record._request_package_name = payload.package_name
    record._request_package_version = payload.package_version

    if record.expires_at and now > record.expires_at:
        record.active = False
        record.revoked_reason = "expired"
        record.deactivated_at = now
        record.updated_at = now
        db.commit()
        return {"valid": False, "status": "expired", "reason": "license_expired"}

    if record.machine_fingerprint and record.machine_fingerprint != payload.machine_fingerprint:
        return {"valid": False, "status": "mismatch", "reason": "machine_fingerprint_mismatch"}

    if not record.active:
        if record.revoked_reason == "payment_failed" and record.grace_until and now <= record.grace_until:
            record.last_verified_at = now
            db.commit()
            return _signed_verify_envelope(record, "payment_failed", payload.machine_fingerprint)
        return {"valid": False, "status": "inactive", "reason": record.revoked_reason or "license_inactive"}

    record.last_verified_at = now
    record.updated_at = now
    db.commit()
    return _signed_verify_envelope(record, "active", payload.machine_fingerprint)


@app.post("/deactivate", response_model=VerifyResponse)
async def deactivate_license(
    payload: DeactivateRequest,
    x_admin_token: Optional[str] = Header(None, alias="X-Admin-Token"),
    db: Session = Depends(get_db),
):
    _admin_guard(x_admin_token)
    raw_key = _normalize_key(payload.license_key)
    record = db.query(LicenseKey).filter(LicenseKey.key_hash == _key_hash(raw_key)).first()
    if not record:
        raise HTTPException(status_code=404, detail="License not found")

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    record.active = False
    record.revoked_reason = payload.reason or "manual"
    record.deactivated_at = now
    record.grace_until = None
    record.updated_at = now
    db.commit()
    db.refresh(record)
    return _serialize_license(record)
