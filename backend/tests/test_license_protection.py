from __future__ import annotations

import asyncio
import base64
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from license.client_verifier import LicenseVerificationError, verify_signed_license_response
from license.heartbeat import build_heartbeat_payload
from license.offline_cache import verify_signed_cache, write_signed_cache
from license.package_guard import PackageTamperError, verify_package_manifest
from license.server_signing import sign_license_payload
from license.validator import LicenseValidationResult, enforce_license_on_startup


def _keypair():
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")
    return private_key, public_key


def _payload(*, fingerprint="fp-1", status="active", expires_delta=30, grace_delta=3, offline_delta=7):
    now = datetime.now(timezone.utc)
    return {
        "license_id": "lic_123",
        "workspace_id": "ws_123",
        "tier": "pro",
        "features": {"edge_control_layer": True},
        "machine_fingerprint": fingerprint,
        "package_name": "veklom-backend",
        "package_version": "1.0.0",
        "issued_at": now.isoformat(),
        "expires_at": (now + timedelta(days=expires_delta)).isoformat(),
        "grace_until": (now + timedelta(days=grace_delta)).isoformat(),
        "offline_until": (now + timedelta(days=offline_delta)).isoformat(),
        "status": status,
    }


def _envelope(private_key, payload):
    return sign_license_payload(payload, private_key=private_key)


def test_valid_signed_license_passes():
    private_key, public_key = _keypair()
    result = verify_signed_license_response(
        _envelope(private_key, _payload()),
        public_key_text=public_key,
        machine_fingerprint="fp-1",
        package_name="veklom-backend",
        package_version="1.0.0",
    )
    assert result.valid is True
    assert result.tier == "pro"
    assert result.features["edge_control_layer"] is True


def test_invalid_signature_fails():
    private_key, public_key = _keypair()
    envelope = _envelope(private_key, _payload())
    envelope["payload"]["tier"] = "enterprise"
    with pytest.raises(LicenseVerificationError):
        verify_signed_license_response(
            envelope,
            public_key_text=public_key,
            machine_fingerprint="fp-1",
            package_name="veklom-backend",
            package_version="1.0.0",
        )


def test_wrong_machine_fingerprint_fails():
    private_key, public_key = _keypair()
    with pytest.raises(LicenseVerificationError):
        verify_signed_license_response(
            _envelope(private_key, _payload(fingerprint="fp-2")),
            public_key_text=public_key,
            machine_fingerprint="fp-1",
            package_name="veklom-backend",
            package_version="1.0.0",
        )


def test_expired_trial_fails_after_grace():
    private_key, public_key = _keypair()
    payload = _payload(status="trial", expires_delta=-5, grace_delta=-1)
    with pytest.raises(LicenseVerificationError):
        verify_signed_license_response(
            _envelope(private_key, payload),
            public_key_text=public_key,
            machine_fingerprint="fp-1",
            package_name="veklom-backend",
            package_version="1.0.0",
        )


def test_payment_failed_within_grace_passes_with_warning_status():
    private_key, public_key = _keypair()
    result = verify_signed_license_response(
        _envelope(private_key, _payload(status="payment_failed", expires_delta=30, grace_delta=3)),
        public_key_text=public_key,
        machine_fingerprint="fp-1",
        package_name="veklom-backend",
        package_version="1.0.0",
    )
    assert result.valid is True
    assert result.status == "payment_failed"


def test_payment_failed_after_grace_fails():
    private_key, public_key = _keypair()
    with pytest.raises(LicenseVerificationError):
        verify_signed_license_response(
            _envelope(private_key, _payload(status="payment_failed", grace_delta=-1)),
            public_key_text=public_key,
            machine_fingerprint="fp-1",
            package_name="veklom-backend",
            package_version="1.0.0",
        )


def test_license_server_offline_with_valid_cache_passes(tmp_path):
    private_key, public_key = _keypair()
    envelope = _envelope(private_key, _payload(offline_delta=2))
    verified = verify_signed_license_response(
        envelope,
        public_key_text=public_key,
        machine_fingerprint="fp-1",
        package_name="veklom-backend",
        package_version="1.0.0",
    )
    cache_path = tmp_path / "license-cache.json"
    write_signed_cache(cache_path, envelope, verified)

    cached = verify_signed_cache(
        cache_path,
        public_key_text=public_key,
        machine_fingerprint="fp-1",
        package_name="veklom-backend",
        package_version="1.0.0",
    )
    assert cached.valid is True


def test_license_server_offline_after_offline_until_fails(tmp_path):
    private_key, public_key = _keypair()
    envelope = _envelope(private_key, _payload(offline_delta=-1))
    verified = verify_signed_license_response(
        envelope,
        public_key_text=public_key,
        machine_fingerprint="fp-1",
        package_name="veklom-backend",
        package_version="1.0.0",
    )
    cache_path = tmp_path / "license-cache.json"
    write_signed_cache(cache_path, envelope, verified)
    with pytest.raises(LicenseVerificationError):
        verify_signed_cache(
            cache_path,
            public_key_text=public_key,
            machine_fingerprint="fp-1",
            package_name="veklom-backend",
            package_version="1.0.0",
        )


def test_tampered_package_manifest_fails(tmp_path):
    private_key, public_key = _keypair()
    critical = tmp_path / "license" / "client_verifier.py"
    critical.parent.mkdir()
    critical.write_text("print('ok')", encoding="utf-8")
    digest = __import__("hashlib").sha256(critical.read_bytes()).hexdigest()
    manifest = {
        "package": "veklom-backend",
        "critical_files": [{"path": "license/client_verifier.py", "sha256": digest}],
    }
    signature = base64.b64encode(private_key.sign(json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8"))).decode("ascii")
    (tmp_path / "package_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (tmp_path / "package_manifest.sig").write_text(signature, encoding="utf-8")
    (tmp_path / "license_public_key.pem").write_text(public_key, encoding="utf-8")
    critical.write_text("print('tampered')", encoding="utf-8")

    with pytest.raises(PackageTamperError):
        verify_package_manifest(tmp_path)


def test_startup_gate_blocks_invalid_license(monkeypatch):
    async def invalid_once():
        return LicenseValidationResult(
            valid=False,
            status="invalid",
            reason="invalid_signature",
            checked_at=datetime.now(timezone.utc),
            machine_fingerprint="fp-1",
        )

    monkeypatch.setattr("license.validator.verify_license_once", invalid_once)
    with pytest.raises(SystemExit):
        asyncio.run(enforce_license_on_startup())


def test_heartbeat_payload_contains_no_customer_data():
    payload = build_heartbeat_payload(
        license_id="lic_123",
        workspace_id="ws_123",
        package_version="1.0.0",
        machine_fingerprint="fp-1",
        started_at=datetime.now(timezone.utc),
        status="active",
    )
    assert set(payload) == {
        "license_id",
        "workspace_id",
        "package_version",
        "machine_fingerprint",
        "started_at",
        "last_seen",
        "status",
    }
    assert "prompt" not in payload
    assert "logs" not in payload
    assert "secret" not in payload
