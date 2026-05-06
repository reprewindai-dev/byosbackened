"""Remote license validation for startup and runtime rechecks."""
from __future__ import annotations

import asyncio
import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

import httpx

from core.config import get_settings
from license.client_verifier import LicenseVerificationError, verify_signed_license_response
from license.machine_fingerprint import get_machine_fingerprint
from license.offline_cache import verify_signed_cache, write_signed_cache

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class LicenseValidationResult:
    valid: bool
    status: str
    reason: str
    checked_at: datetime
    machine_fingerprint: str
    license_key_prefix: str = ""
    workspace_id: str = ""
    tier: str = ""
    expires_at: Optional[datetime] = None
    grace_until: Optional[datetime] = None
    offline_until: Optional[datetime] = None
    license_id: str = ""
    features: Optional[dict[str, Any]] = None
    raw: Optional[dict[str, Any]] = None


_LICENSE_RESULT: Optional[LicenseValidationResult] = None


def _parse_dt(value: Any) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        text = str(value).replace("Z", "+00:00")
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def _normalize_verify_url(url: str) -> str:
    url = (url or "").strip().rstrip("/")
    if not url:
        return ""
    if url.endswith("/verify"):
        return url
    return f"{url}/verify"


def _cache_path() -> Path:
    settings = get_settings()
    configured = (settings.license_cache_path or os.getenv("LICENSE_CACHE_PATH", "")).strip()
    if configured:
        return Path(configured).expanduser().resolve()
    return (Path.home() / ".veklom" / "license-cache.json").resolve()


def _public_key_text() -> str:
    settings = get_settings()
    if settings.license_public_key:
        return settings.license_public_key
    path = Path(settings.license_public_key_path or "license_public_key.pem")
    if not path.is_absolute():
        path = Path.cwd() / path
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _serialize_result(result: LicenseValidationResult) -> dict[str, Any]:
    settings = get_settings()
    cache_grace_hours = int(settings.license_cache_grace_hours or 48)
    grace_until = result.grace_until or (result.checked_at + timedelta(hours=cache_grace_hours))
    return {
        "key": result.license_key_prefix,
        "valid": result.valid,
        "status": result.status,
        "reason": result.reason,
        "last_verified": result.checked_at.isoformat(),
        "grace_until": grace_until.isoformat() if grace_until else None,
        "expires_at": result.expires_at.isoformat() if result.expires_at else None,
        "workspace_id": result.workspace_id,
        "tier": result.tier,
        "offline_until": result.offline_until.isoformat() if result.offline_until else None,
        "license_id": result.license_id,
        "machine_fingerprint": result.machine_fingerprint,
    }


def _write_cache(result: LicenseValidationResult) -> None:
    try:
        path = _cache_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(_serialize_result(result), indent=2, sort_keys=True), encoding="utf-8")
    except Exception as exc:
        logger.warning("Failed to write license cache: %s", exc)


def _read_cache() -> Optional[dict[str, Any]]:
    try:
        path = _cache_path()
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Failed to read license cache: %s", exc)
        return None


def _get_license_key() -> str:
    settings = get_settings()
    return (settings.license_key or os.getenv("LICENSE_KEY", "")).strip()


def _should_enforce_license() -> bool:
    settings = get_settings()
    return bool(settings.license_enforcement_enabled or _get_license_key())


def _build_payload() -> dict[str, Any]:
    settings = get_settings()
    return {
        "license_key": _get_license_key(),
        "machine_fingerprint": get_machine_fingerprint(),
        "workspace_id": os.getenv("WORKSPACE_ID", ""),
        "hostname": os.getenv("HOSTNAME", ""),
        "app_name": settings.app_name,
        "app_version": settings.app_version,
        "package_name": settings.package_name,
        "package_version": settings.package_version or settings.app_version,
    }


def cache_license_result(result: LicenseValidationResult) -> None:
    global _LICENSE_RESULT
    _LICENSE_RESULT = result


def get_cached_license_result() -> Optional[LicenseValidationResult]:
    return _LICENSE_RESULT


async def verify_license_once() -> LicenseValidationResult:
    settings = get_settings()
    verify_urls = [
        url for url in [_normalize_verify_url(settings.license_verify_url)] if url
    ]
    backup_url = _normalize_verify_url(settings.license_verify_backup_url)
    if backup_url and backup_url not in verify_urls:
        verify_urls.append(backup_url)
    license_key = _get_license_key()
    machine_fingerprint = get_machine_fingerprint()
    now = datetime.now(timezone.utc)

    if not _should_enforce_license():
        result = LicenseValidationResult(
            valid=True,
            status="disabled",
            reason="license_enforcement_disabled",
            checked_at=now,
            machine_fingerprint=machine_fingerprint,
        )
        cache_license_result(result)
        return result

    if not license_key:
        result = LicenseValidationResult(
            valid=False,
            status="missing",
            reason="license_key_missing",
            checked_at=now,
            machine_fingerprint=machine_fingerprint,
        )
        cache_license_result(result)
        return result

    if not verify_urls:
        result = LicenseValidationResult(
            valid=False,
            status="misconfigured",
            reason="license_verify_url_missing",
            checked_at=now,
            machine_fingerprint=machine_fingerprint,
            license_key_prefix=license_key[:8],
        )
        cache_license_result(result)
        return result

    timeout = httpx.Timeout(3.0, connect=1.0)
    payload = None
    last_error: Optional[Exception] = None
    async with httpx.AsyncClient(timeout=timeout) as client:
        for verify_url in verify_urls:
            try:
                response = await client.post(verify_url, json=_build_payload())
                response.raise_for_status()
                payload = response.json()
                break
            except Exception as exc:
                last_error = exc
                logger.warning("License verify endpoint failed (%s): %s", verify_url, exc)
                continue

    if payload is None:
        try:
            verified = verify_signed_cache(
                _cache_path(),
                public_key_text=_public_key_text(),
                machine_fingerprint=machine_fingerprint,
                package_name=settings.package_name,
                package_version=settings.package_version or settings.app_version,
                now=now,
            )
            result = LicenseValidationResult(
                valid=True,
                status="cached",
                reason="license_server_unreachable_cache_valid",
                checked_at=now,
                machine_fingerprint=machine_fingerprint,
                workspace_id=verified.workspace_id,
                tier=verified.tier,
                expires_at=verified.expires_at,
                grace_until=verified.grace_until,
                offline_until=verified.offline_until,
                license_id=verified.license_id,
                features=verified.features,
                raw={"signed_cache": True, "error": str(last_error) if last_error else ""},
            )
            cache_license_result(result)
            return result
        except LicenseVerificationError as exc:
            logger.warning("Signed offline license cache rejected: %s", exc)

        result = LicenseValidationResult(
            valid=False,
            status="unreachable",
            reason="license_server_unreachable",
            checked_at=now,
            machine_fingerprint=machine_fingerprint,
            raw={"error": str(last_error) if last_error else ""},
        )
        cache_license_result(result)
        return result

    try:
        verified = verify_signed_license_response(
            payload,
            public_key_text=_public_key_text(),
            machine_fingerprint=machine_fingerprint,
            package_name=settings.package_name,
            package_version=settings.package_version or settings.app_version,
            now=now,
        )
    except LicenseVerificationError as exc:
        result = LicenseValidationResult(
            valid=False,
            status="invalid",
            reason=str(exc),
            checked_at=now,
            machine_fingerprint=machine_fingerprint,
            raw={"signed_response_error": str(exc)},
        )
        cache_license_result(result)
        return result

    result = LicenseValidationResult(
        valid=True,
        status=verified.status,
        reason=verified.reason,
        checked_at=now,
        machine_fingerprint=machine_fingerprint,
        workspace_id=verified.workspace_id,
        tier=verified.tier,
        expires_at=verified.expires_at,
        grace_until=verified.grace_until,
        offline_until=verified.offline_until,
        license_id=verified.license_id,
        features=verified.features,
        raw=payload,
    )
    cache_license_result(result)
    write_signed_cache(_cache_path(), payload, verified)
    return result


async def enforce_license_on_startup() -> LicenseValidationResult:
    """Validate the local license and terminate the process on hard failure."""
    settings = get_settings()
    try:
        result = await verify_license_once()
    except Exception as exc:
        logger.critical("License verification failed: %s", exc)
        raise SystemExit(1) from exc

    if result.valid:
        if result.status == "cached" and result.grace_until:
            logger.warning(
                "License server unavailable; using local grace cache until %s",
                result.grace_until.isoformat(),
            )
        elif result.status == "grace" and result.grace_until:
            logger.warning("License is in grace mode until %s", result.grace_until.isoformat())
        else:
            logger.info("License validated successfully for tier=%s", result.tier or "unknown")
        return result

    if result.reason == "payment_failed" and result.grace_until:
        grace_hours = int(settings.license_grace_hours or 72)
        if result.grace_until > datetime.now(timezone.utc):
            logger.warning(
                "License payment failure is within the %s hour grace window until %s",
                grace_hours,
                result.grace_until.isoformat(),
            )
            return result

    logger.critical("License validation failed: status=%s reason=%s", result.status, result.reason)
    raise SystemExit(1)


def enforce_license_sync() -> LicenseValidationResult:
    """Synchronous helper for callers that cannot await startup."""
    return asyncio.run(enforce_license_on_startup())
