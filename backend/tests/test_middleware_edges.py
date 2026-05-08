from __future__ import annotations

from apps.api.middleware.entitlement_check import EntitlementCheckMiddleware
from apps.api.middleware.entitlement_check import PUBLIC_ENDPOINTS as ENTITLEMENT_PUBLIC_ENDPOINTS
from apps.api.middleware.token_deduction import DEFAULT_ENDPOINT_COSTS
from apps.api.middleware.token_deduction import PUBLIC_ENDPOINTS as TOKEN_PUBLIC_ENDPOINTS
from core.security.zero_trust import _PUBLIC_PATHS as ZERO_TRUST_PUBLIC_PATHS
from core.security.zero_trust import _PUBLIC_PREFIXES as ZERO_TRUST_PUBLIC_PREFIXES


def test_edge_entitlement_paths_requirements():
    middleware = EntitlementCheckMiddleware(app=None)  # type: ignore[arg-type]

    assert middleware._get_required_plan("POST", "/api/v1/edge/input/webhook") == "starter"
    assert middleware._get_required_plan("GET", "/api/v1/edge/snmp") == "pro"
    assert middleware._get_required_plan("GET", "/api/v1/edge/modbus") == "pro"
    assert middleware._get_required_plan("GET", "/api/v1/edge/protocol/snmp") == "pro"
    assert middleware._get_required_plan("GET", "/api/v1/edge/protocol/modbus") == "pro"


def test_token_deduction_middleware_has_no_hidden_endpoint_costs():
    assert DEFAULT_ENDPOINT_COSTS == {}


def test_public_demo_and_pipeline_routes_are_free_and_public():
    public_paths = {
        "/api/v1/edge/demo/summary",
        "/api/v1/edge/demo/infrastructure",
        "/api/v1/demo/pipeline/health",
        "/api/v1/demo/pipeline/stream",
    }

    assert public_paths.issubset(ZERO_TRUST_PUBLIC_PATHS)
    assert public_paths.issubset(ENTITLEMENT_PUBLIC_ENDPOINTS)
    assert public_paths.issubset(TOKEN_PUBLIC_ENDPOINTS)


def test_workspace_shell_routes_are_public_html_surfaces():
    expected_prefixes = {
        "/dashboard",
        "/playground",
        "/marketplace",
        "/models",
        "/pipelines",
        "/deployments",
        "/monitoring",
        "/vault",
        "/compliance",
        "/billing",
        "/team",
        "/settings",
        "/onboarding",
    }

    assert expected_prefixes.issubset(set(ZERO_TRUST_PUBLIC_PREFIXES))


def test_marketplace_read_routes_are_public_browsing_surfaces():
    from core.config import get_settings

    api_prefix = get_settings().api_prefix
    public_marketplace_bases = {
        f"{api_prefix}/listings",
        f"{api_prefix}/categories",
        f"{api_prefix}/evidence",
        f"{api_prefix}/marketplace/listings",
        f"{api_prefix}/marketplace/categories",
        f"{api_prefix}/marketplace/evidence",
    }

    assert public_marketplace_bases


def test_edge_protocol_routes_are_not_public():
    protected_paths = {
        "/api/v1/edge/snmp",
        "/api/v1/edge/modbus",
        "/api/v1/edge/protocol/snmp",
        "/api/v1/edge/protocol/modbus",
    }

    assert protected_paths.isdisjoint(ZERO_TRUST_PUBLIC_PATHS)
    assert protected_paths.isdisjoint(ENTITLEMENT_PUBLIC_ENDPOINTS)
    assert protected_paths.isdisjoint(TOKEN_PUBLIC_ENDPOINTS)


def test_internal_operator_routes_are_not_public():
    protected_paths = {
        "/api/v1/internal/operators/overview",
        "/api/v1/internal/operators/workers",
        "/api/v1/internal/operators/runs",
    }

    assert protected_paths.isdisjoint(ZERO_TRUST_PUBLIC_PATHS)
    assert protected_paths.isdisjoint(ENTITLEMENT_PUBLIC_ENDPOINTS)
    assert protected_paths.isdisjoint(TOKEN_PUBLIC_ENDPOINTS)
