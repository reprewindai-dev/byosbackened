"""Build a buyer-facing backend zip and exclude server-side license files."""
from __future__ import annotations

import argparse
import fnmatch
from pathlib import Path
import zipfile


ROOT = Path(__file__).resolve().parents[1]

# Buyer-facing runtime surface. Everything else stays out of the download zip.
BUYER_DIRS = {
    "apps",
    "config",
    "core",
    "db",
    "infra",
    "landing",
    "license",
    "public",
    "static",
    "acquisition",
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

# Files that stay on the seller-side license server and must not ship to buyers.
SERVER_ONLY_EXACT = {
    "license/server.py",
    "license/stripe_webhook.py",
    "db/models/license_key.py",
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
}

EXCLUDED_GLOBS = {
    "*.pyc",
    "*.pyo",
    "*.log",
    "*.sqlite",
    "*.db",
    "*.zip",
    ".env",
    ".env.*",
    "*_secret*",
    "*secret*",
    "*password*",
}


def should_include(path: Path) -> bool:
    rel = path.relative_to(ROOT).as_posix()
    parts = rel.split("/")

    if rel in SERVER_ONLY_EXACT:
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


def build_zip(tier: str, version: str, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    zip_path = output_dir / f"veklom-backend-{tier}-{version}.zip"

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for file_path in ROOT.rglob("*"):
            if not file_path.is_file():
                continue
            if not should_include(file_path):
                continue
            rel = file_path.relative_to(ROOT)
            bundle.write(file_path, rel.as_posix())

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
