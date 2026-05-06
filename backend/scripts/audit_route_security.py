from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from apps.api.main import app  # noqa: E402
from core.config import get_settings  # noqa: E402
from core.security.zero_trust import (  # noqa: E402
    _PUBLIC_PATHS,
    _PUBLIC_PREFIXES,
    _PUBLIC_STATIC_SUFFIXES,
)


SENSITIVE_PREFIXES = (
    "/api/v1/admin",
    "/api/v1/internal",
    "/api/v1/locker",
    "/api/v1/security",
    "/api/v1/workspace",
    "/api/v1/wallet",
    "/api/v1/billing",
    "/api/v1/budget",
    "/api/v1/cost",
    "/api/v1/audit",
    "/api/v1/privacy",
    "/api/v1/pipelines",
    "/api/v1/deployments",
    "/api/v1/content-safety",
    "/api/v1/autonomous",
    "/api/v1/insights",
    "/api/v1/suggestions",
    "/api/v1/plugins",
    "/api/v1/explain",
    "/api/v1/monitoring",
    "/api/v1/routing",
    "/api/v1/auth/api-keys",
    "/api/v1/auth/me",
    "/api/v1/auth/mfa",
    "/api/v1/auth/connected-accounts",
    "/api/v1/auth/github/repos",
    "/api/v1/edge/input",
    "/api/v1/edge/ingest",
    "/api/v1/edge/control",
    "/api/v1/edge/protocol",
    "/api/v1/edge/snmp",
    "/api/v1/edge/modbus",
)


@dataclass(frozen=True)
class RouteSecurityRecord:
    method: str
    path: str
    public: bool
    reason: str


def _normalize_path(path: str) -> str:
    if len(path) > 1:
        return path.rstrip("/")
    return path


def public_marketplace_bases() -> tuple[str, ...]:
    api_prefix = get_settings().api_prefix
    return (
        f"{api_prefix}/listings",
        f"{api_prefix}/categories",
        f"{api_prefix}/evidence",
        f"{api_prefix}/marketplace/listings",
        f"{api_prefix}/marketplace/categories",
        f"{api_prefix}/marketplace/evidence",
    )


def classify_route(method: str, path: str) -> tuple[bool, str]:
    normalized = _normalize_path(path)
    method = method.upper()

    if normalized in _PUBLIC_PATHS:
        return True, "zero_trust_public_path"

    if method == "GET":
        for base in public_marketplace_bases():
            if normalized == base or normalized.startswith(base + "/"):
                return True, "public_marketplace_read"

    if normalized.endswith(_PUBLIC_STATIC_SUFFIXES):
        return True, "public_static_asset"

    for prefix in _PUBLIC_PREFIXES:
        if normalized == prefix or normalized.startswith(prefix + "/"):
            return True, "public_web_surface"

    return False, "auth_required"


def iter_route_security() -> Iterable[RouteSecurityRecord]:
    for route in app.routes:
        path = getattr(route, "path", "")
        if not path:
            continue
        methods = sorted((getattr(route, "methods", None) or set()) - {"HEAD", "OPTIONS"})
        for method in methods:
            public, reason = classify_route(method, path)
            yield RouteSecurityRecord(method=method, path=path, public=public, reason=reason)


def sensitive_public_violations(
    records: Iterable[RouteSecurityRecord],
) -> list[RouteSecurityRecord]:
    violations: list[RouteSecurityRecord] = []
    for record in records:
        if not record.public:
            continue
        if any(record.path == prefix or record.path.startswith(prefix + "/") for prefix in SENSITIVE_PREFIXES):
            violations.append(record)
    return violations


def build_report() -> dict[str, object]:
    records = sorted(iter_route_security(), key=lambda item: (item.path, item.method))
    public_records = [record for record in records if record.public]
    protected_records = [record for record in records if not record.public]
    violations = sensitive_public_violations(records)

    return {
        "route_count": len(records),
        "public_count": len(public_records),
        "protected_count": len(protected_records),
        "sensitive_public_violations": [asdict(record) for record in violations],
        "public_routes": [asdict(record) for record in public_records],
    }


def main() -> int:
    report = build_report()
    print(json.dumps(report, indent=2, sort_keys=True))
    return 1 if report["sensitive_public_violations"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
