"""Audit FastAPI route exposure and critical response contracts."""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.api.main import app


PUBLIC_200_ROUTES = (
    "/health",
    "/status",
    "/api/v1/demo/pipeline/health",
    "/api/v1/edge/demo/summary",
    "/api/v1/edge/demo/infrastructure?scenario=network&live=false",
    "/api/v1/edge/demo/infrastructure?scenario=machine&live=false",
)

PROTECTED_ROUTES = (
    "/api/v1/edge/protocol/snmp",
    "/api/v1/edge/protocol/modbus",
    "/api/v1/jobs/process",
    "/api/v1/marketplace/automation/run",
    "/api/v1/internal/operators/overview",
)


def _registered_paths() -> list[str]:
    paths: list[str] = []
    for route in app.routes:
        path = getattr(route, "path", "")
        if path:
            paths.append(path)
    return sorted(paths)


def main() -> int:
    paths = _registered_paths()
    counts = Counter(paths)
    print(f"registered_routes={len(paths)} unique_routes={len(counts)}")

    required_paths = {
        "/health",
        "/api/v1/edge/demo/summary",
        "/api/v1/edge/demo/infrastructure",
        "/api/v1/edge/protocol/snmp",
        "/api/v1/edge/protocol/modbus",
        "/api/v1/jobs/process",
        "/api/v1/marketplace/automation/run",
        "/api/v1/internal/operators/overview",
    }
    missing = sorted(required_paths - set(paths))
    if missing:
        print("missing_required_routes=" + ",".join(missing))
        return 1

    client = TestClient(app)
    failures: list[str] = []

    for route in PUBLIC_200_ROUTES:
        response = client.get(route)
        print(f"public {route} -> {response.status_code}")
        if response.status_code != 200:
            failures.append(f"{route} expected 200 got {response.status_code}")

    for route in PROTECTED_ROUTES:
        method = client.post if route.endswith("/process") or route.endswith("/run") else client.get
        response = method(route)
        print(f"protected {route} -> {response.status_code}")
        if response.status_code != 401:
            failures.append(f"{route} expected 401 got {response.status_code}")

    if failures:
        for failure in failures:
            print("FAIL " + failure)
        return 1
    print("route_audit_ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
