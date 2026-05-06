from __future__ import annotations

from scripts.audit_route_security import (
    build_report,
    classify_route,
    iter_route_security,
    sensitive_public_violations,
)


def test_sensitive_route_families_are_not_public():
    violations = sensitive_public_violations(iter_route_security())
    assert violations == []


def test_public_edge_demo_routes_remain_intentionally_public():
    assert classify_route("GET", "/api/v1/edge/demo/summary") == (
        True,
        "zero_trust_public_path",
    )
    assert classify_route("GET", "/api/v1/edge/demo/infrastructure") == (
        True,
        "zero_trust_public_path",
    )


def test_edge_customer_and_protocol_routes_remain_protected():
    protected_routes = {
        ("POST", "/api/v1/edge/input/webhook"),
        ("GET", "/api/v1/edge/protocol/snmp"),
        ("GET", "/api/v1/edge/protocol/modbus"),
        ("GET", "/api/v1/edge/snmp"),
        ("GET", "/api/v1/edge/modbus"),
    }

    for method, path in protected_routes:
        assert classify_route(method, path) == (False, "auth_required")


def test_internal_operator_and_workspace_routes_remain_protected():
    protected_routes = {
        ("GET", "/api/v1/internal/operators/overview"),
        ("GET", "/api/v1/internal/operators/workers"),
        ("POST", "/api/v1/internal/operators/runs"),
        ("GET", "/api/v1/workspace/overview"),
        ("GET", "/api/v1/workspace/members"),
        ("GET", "/api/v1/auth/api-keys"),
        ("POST", "/api/v1/auth/api-keys"),
    }

    for method, path in protected_routes:
        assert classify_route(method, path) == (False, "auth_required")


def test_marketplace_read_surfaces_are_public_but_write_surfaces_are_not():
    assert classify_route("GET", "/api/v1/listings") == (
        True,
        "public_marketplace_read",
    )
    assert classify_route("GET", "/api/v1/marketplace/listings/example") == (
        True,
        "public_marketplace_read",
    )
    assert classify_route("POST", "/api/v1/listings/create") == (
        False,
        "auth_required",
    )
    assert classify_route("POST", "/api/v1/marketplace/listings/review") == (
        False,
        "auth_required",
    )


def test_route_security_report_counts_every_runtime_route():
    report = build_report()

    assert report["route_count"] >= 250
    assert report["protected_count"] > report["public_count"]
    assert report["sensitive_public_violations"] == []
