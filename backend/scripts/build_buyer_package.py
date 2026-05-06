"""Build a clean customer-facing Veklom backend release archive.

The source repository contains operator-only deployment state, marketing pages,
local databases, logs, stress artifacts, and secret environment files. This
builder is the hard boundary for customer downloads: only backend runtime code,
sanitized templates, and deployment scaffolding are allowed into the archive.
"""
from __future__ import annotations

import argparse
import base64
import fnmatch
import hashlib
import json
import os
from pathlib import Path
import re
import zipfile

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_NAME = "veklom-backend"

# Customer-facing backend runtime surface. Everything else stays out of the zip.
BUYER_DIRS = {
    "apps",
    "config",
    "core",
    "db",
    "edge",
    "infra",
    "license",
    "public",
    "static",
}

BUYER_ROOT_FILES = {
    "README.md",
    "alembic.ini",
    "pyproject.toml",
    "gunicorn_conf.py",
    "docker-compose.yaml",
    "docker-compose.dev.yml",
    "docker-compose.prod.yml",
    ".env.example",
    ".env.production.example",
}

# Files that stay on the Veklom-operated license/billing side.
SERVER_ONLY_EXACT = {
    "apps/api/routers/internal_operators.py",
    "license/server.py",
    "license/stripe_webhook.py",
    "db/models/license_key.py",
    "license/private_signing_key.pem",
}

CRITICAL_FILES = {
    "apps/api/main.py",
    "apps/api/middleware/entitlement_check.py",
    "apps/api/middleware/token_deduction.py",
    "core/security/zero_trust.py",
    "license/client_verifier.py",
    "license/machine_fingerprint.py",
    "license/offline_cache.py",
    "license/package_guard.py",
    "license/middleware.py",
    "license/validator.py",
}

OPERATOR_ONLY_DIRS = {
    "acquisition",
    "landing",
    "docs",
    "tests",
    "scripts",
}

EXCLUDED_DIRS = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".venv",
    "venv",
    "dist",
    "build",
    "byos_ai_backend.egg-info",
}

EXCLUDED_GLOBS = {
    "*.pyc",
    "*.pyo",
    "*.log",
    "*.csv",
    "*.json",
    "*.sqlite",
    "*.db",
    "*.zip",
    ".env",
    ".env.*",
    "*_secret*",
    "*secret*",
    "*password*",
    "server.log",
    "stress_results*",
    "stress_test_*",
}

SECRET_VALUE_PATTERNS = [
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"sk_live_[0-9A-Za-z]{16,}"),
    re.compile(r"rk_live_[0-9A-Za-z]{16,}"),
    re.compile(r"whsec_[0-9A-Za-z]{16,}"),
    re.compile(r"xox[baprs]-[0-9A-Za-z-]{20,}"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |)PRIVATE KEY-----"),
]

SENSITIVE_ENV_MARKERS = ("SECRET", "PASSWORD", "PRIVATE_KEY", "ACCESS_KEY", "API_KEY", "WEBHOOK_SECRET", "ADMIN_TOKEN")
NON_SECRET_ENV_KEYS = {
    "ACCESS_TOKEN_EXPIRE_MINUTES",
    "REFRESH_TOKEN_EXPIRE_DAYS",
    "LLM_MAX_TOKENS",
    "LICENSE_CACHE_GRACE_HOURS",
    "SMTP_USE_TLS",
    "GITHUB_REDIRECT_URI",
}
PLACEHOLDER_PREFIXES = ("CHANGE_ME", "GENERATE_", "REQUIRED_", "your_", "example", "placeholder", "null", "none")
PLACEHOLDER_VALUES = {"", "...", "minioadmin"}


def should_include(path: Path) -> bool:
    rel = path.relative_to(ROOT).as_posix()
    parts = rel.split("/")

    if rel in SERVER_ONLY_EXACT:
        return False
    if parts[0] in OPERATOR_ONLY_DIRS:
        return False
    if parts[0] not in BUYER_DIRS and rel not in BUYER_ROOT_FILES:
        return False
    if any(part in EXCLUDED_DIRS for part in parts):
        return False
    if parts[0] == "license" and rel == "license/tier.py":
        return True
    if rel in BUYER_ROOT_FILES:
        return True
    if len(parts) > 1 and parts[0] == "license" and parts[1] in {"__init__.py", "fingerprint.py", "middleware.py", "tier.py", "validator.py"}:
        return True
    if len(parts) > 1 and parts[0] in BUYER_DIRS:
        if any(fnmatch.fnmatch(path.name, pattern) for pattern in EXCLUDED_GLOBS):
            return False
        return True
    if any(fnmatch.fnmatch(path.name, pattern) for pattern in EXCLUDED_GLOBS):
        return False
    return True


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_text_file(path: Path) -> bool:
    return path.suffix.lower() in {
        ".py",
        ".toml",
        ".yml",
        ".yaml",
        ".ini",
        ".md",
        ".txt",
        ".json",
        ".html",
        ".css",
        ".js",
        ".svg",
        ".example",
    } or path.name.startswith(".env")


def scan_file_for_secret_material(path: Path) -> list[str]:
    """Return redacted secret-scan findings for one file."""
    findings: list[str] = []
    if not _is_text_file(path):
        return findings
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except OSError as exc:
        return [f"read_error:{exc}"]

    for pattern in SECRET_VALUE_PATTERNS:
        if pattern.search(content):
            findings.append(f"secret_value_pattern:{pattern.pattern[:32]}")
    if path.name.startswith(".env") or path.suffix.lower() in {".env", ".example"}:
        for line in content.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            key = key.strip().upper()
            value = value.strip().strip('"').strip("'")
            if key in NON_SECRET_ENV_KEYS:
                continue
            if not any(marker in key for marker in SENSITIVE_ENV_MARKERS):
                continue
            lower_value = value.lower()
            if value in PLACEHOLDER_VALUES or any(value.startswith(prefix) for prefix in PLACEHOLDER_PREFIXES):
                continue
            if lower_value in PLACEHOLDER_VALUES or any(lower_value.startswith(prefix.lower()) for prefix in PLACEHOLDER_PREFIXES):
                continue
            if value.endswith("..."):
                continue
            findings.append(f"non_placeholder_secret_assignment:{key}")
    return findings


def collect_package_files() -> list[Path]:
    files: list[Path] = []
    for file_path in ROOT.rglob("*"):
        if file_path.is_file() and should_include(file_path):
            files.append(file_path)
    return sorted(files, key=lambda item: item.relative_to(ROOT).as_posix())


def build_manifest(*, tier: str, version: str, files: list[Path]) -> dict:
    file_rows = [
        {
            "path": file_path.relative_to(ROOT).as_posix(),
            "size": file_path.stat().st_size,
            "sha256": _sha256(file_path),
        }
        for file_path in files
    ]
    return {
        "package": PACKAGE_NAME,
        "tier": tier,
        "version": version,
        "root": "backend",
        "file_count": len(files),
        "included_top_level": sorted(BUYER_DIRS),
        "excluded_operator_surfaces": sorted(OPERATOR_ONLY_DIRS),
        "server_only_exclusions": sorted(SERVER_ONLY_EXACT),
        "critical_files": [row for row in file_rows if row["path"] in CRITICAL_FILES],
        "files": file_rows,
    }


def _canonical_json(data: dict) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


def _load_release_private_key() -> Ed25519PrivateKey:
    key_material = os.getenv("VEKLOM_RELEASE_SIGNING_PRIVATE_KEY", "").strip()
    if key_material:
        try:
            if "BEGIN PRIVATE KEY" in key_material:
                key = serialization.load_pem_private_key(key_material.encode("utf-8"), password=None)
            else:
                key = Ed25519PrivateKey.from_private_bytes(base64.b64decode(key_material))
        except Exception as exc:
            raise RuntimeError("VEKLOM_RELEASE_SIGNING_PRIVATE_KEY is not a valid Ed25519 private key") from exc
        if not isinstance(key, Ed25519PrivateKey):
            raise RuntimeError("VEKLOM_RELEASE_SIGNING_PRIVATE_KEY must be Ed25519")
        return key

    # Development-safe fallback: creates a verifiable package without storing a
    # private key in the archive. Production release jobs should set the env var.
    return Ed25519PrivateKey.generate()


def _public_key_pem(private_key: Ed25519PrivateKey) -> str:
    return private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")


def build_zip(tier: str, version: str, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    zip_path = output_dir / f"{PACKAGE_NAME}-{tier}-{version}.zip"
    files = collect_package_files()
    secret_findings: dict[str, list[str]] = {}

    for file_path in files:
        findings = scan_file_for_secret_material(file_path)
        if findings:
            secret_findings[file_path.relative_to(ROOT).as_posix()] = findings

    if secret_findings:
        raise RuntimeError(
            "Refusing to build customer package; possible secret material found: "
            + json.dumps(secret_findings, sort_keys=True)
        )

    manifest = build_manifest(tier=tier, version=version, files=files)
    release_key = _load_release_private_key()
    signature = base64.b64encode(release_key.sign(_canonical_json(manifest))).decode("ascii")
    public_key = _public_key_pem(release_key)

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for file_path in files:
            rel = file_path.relative_to(ROOT)
            bundle.write(file_path, rel.as_posix())
        bundle.writestr("package_manifest.json", json.dumps(manifest, indent=2, sort_keys=True))
        bundle.writestr("package_manifest.sig", signature)
        bundle.writestr("license_public_key.pem", public_key)
        bundle.writestr("RELEASE_MANIFEST.json", json.dumps(manifest, indent=2, sort_keys=True))

    return zip_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build buyer-facing backend zip")
    parser.add_argument("--tier", required=True, help="Buyer tier label, e.g. starter, pro, sovereign")
    parser.add_argument("--version", required=True, help="Release version label, e.g. 1.0.0")
    parser.add_argument(
        "--output-dir",
        default=str(ROOT / "dist"),
        help="Directory to write the zip file into (default: backend/dist)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    zip_path = build_zip(args.tier.strip().lower(), args.version.strip(), Path(args.output_dir))
    print(str(zip_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
