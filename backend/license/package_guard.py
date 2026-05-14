"""Signed package manifest verification for buyer builds."""
from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from license.client_verifier import canonical_json, load_public_key


class PackageTamperError(RuntimeError):
    """Raised when a signed package manifest or critical file is invalid."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_manifest_signature(manifest: dict[str, Any], signature_text: str, public_key_text: str) -> None:
    signature = base64.b64decode((signature_text or "").strip())
    public_key = load_public_key(public_key_text)
    if not isinstance(public_key, Ed25519PublicKey):
        raise PackageTamperError("package manifest public key must be Ed25519")
    try:
        public_key.verify(signature, canonical_json(manifest))
    except (InvalidSignature, ValueError) as exc:
        raise PackageTamperError("package manifest signature is invalid") from exc


def verify_package_manifest(root: Path, *, manifest_path: Path | None = None) -> None:
    manifest_path = manifest_path or root / "package_manifest.json"
    signature_path = root / "package_manifest.sig"
    public_key_path = root / "license_public_key.pem"

    if not manifest_path.exists():
        raise PackageTamperError("package manifest is missing")
    if not signature_path.exists():
        raise PackageTamperError("package manifest signature is missing")
    if not public_key_path.exists():
        raise PackageTamperError("license public verification key is missing")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    verify_manifest_signature(
        manifest,
        signature_path.read_text(encoding="utf-8"),
        public_key_path.read_text(encoding="utf-8"),
    )

    for item in manifest.get("critical_files", []):
        rel = str(item.get("path") or "")
        expected = str(item.get("sha256") or "")
        if not rel or not expected:
            raise PackageTamperError("package manifest has malformed critical file entry")
        path = root / rel
        if not path.exists():
            raise PackageTamperError(f"critical file missing: {rel}")
        if sha256_file(path) != expected:
            raise PackageTamperError(f"critical file hash mismatch: {rel}")
