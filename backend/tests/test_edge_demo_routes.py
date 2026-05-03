from __future__ import annotations

import asyncio
import pytest
from fastapi import HTTPException
from fastapi.routing import APIRoute

from edge.services.legacy_targets import DemoTarget
from edge.routers import edge_ingest, modbus as modbus_router, snmp as snmp_router


def test_route_paths_exposed():
    from apps.api.main import app

    paths = {(route.path, ",".join(sorted(route.methods or []))) for route in app.routes if isinstance(route, APIRoute)}
    assert ("/api/v1/edge/protocol/snmp", "GET") in paths
    assert ("/api/v1/edge/protocol/modbus", "GET") in paths
    assert ("/api/v1/edge/demo/summary", "GET") in paths
    assert ("/api/v1/edge/demo/infrastructure", "GET") in paths
    assert ("/api/v1/demo/pipeline/health", "GET") in paths
    assert ("/api/v1/demo/pipeline/stream", "GET") in paths
    assert ("/api/v1/marketplace/listings", "GET") in paths
    assert ("/api/v1/marketplace/categories", "GET") in paths


def test_protocol_aliases_work():
    from apps.api.main import app
    route_by_path = {}
    for route in app.routes:
        if isinstance(route, APIRoute) and route.path in {
            "/api/v1/edge/snmp",
            "/api/v1/edge/protocol/snmp",
            "/api/v1/edge/modbus",
            "/api/v1/edge/protocol/modbus",
        }:
            route_by_path[route.path] = route.endpoint

    assert route_by_path["/api/v1/edge/snmp"] is route_by_path["/api/v1/edge/protocol/snmp"]
    assert route_by_path["/api/v1/edge/modbus"] is route_by_path["/api/v1/edge/protocol/modbus"]


def test_public_demo_live_false_no_external_calls(monkeypatch):
    calls = {"resolve": 0, "read": 0}

    monkeypatch.setattr("edge.routers.edge_ingest.resolve_demo_target_for_live", lambda scenario: (_ for _ in ()).throw(AssertionError("resolve called")))
    monkeypatch.setattr("edge.routers.edge_ingest.read_snmp", lambda host, oid: (_ for _ in ()).throw(AssertionError("read called")))

    result = asyncio.run(edge_ingest.demo_infrastructure(scenario="machine", live=False))

    assert result["live"] is False
    assert result["fallback"] is True
    assert result["status"] == "degraded"


def test_public_demo_live_true_uses_allowlist(monkeypatch):
    target = DemoTarget(
        host="demo.pysnmp.com",
        oid="1.3.6.1.2.1.1.3.0",
        metric="sysUpTimeInstance",
        scenario="network",
        title="network",
        description="Core network control-plane checks",
        source="demo.pysnmp.com",
        cost_estimate=40,
    )
    calls = {}

    def fake_resolve(scenario):
        calls["scenario"] = scenario
        return target

    def fake_read(host, oid):
        calls["host"] = host
        calls["oid"] = oid
        return "123"

    monkeypatch.setattr("edge.routers.edge_ingest.resolve_demo_target_for_live", fake_resolve)
    monkeypatch.setattr("edge.routers.edge_ingest.read_snmp", fake_read)

    result = asyncio.run(edge_ingest.demo_infrastructure(scenario="network", live=True))

    assert calls["scenario"] == "network"
    assert calls["host"] == "demo.pysnmp.com"
    assert calls["oid"] == target.oid
    assert result["live"] is True
    assert result["fallback"] is False
    assert result["status"] == "ok"


def test_invalid_ip_oid_is_rejected():
    with pytest.raises(HTTPException):
        asyncio.run(snmp_router.read_snmp_route(target="127-0-0-1", oid_key="bad", user=None))


def test_protocol_routes_reject_raw_target_coordinates():
    request = type("Request", (), {"query_params": {"ip": "127.0.0.1", "oid": "1.3.6.1.2.1.1.1.0"}})()
    with pytest.raises(HTTPException):
        asyncio.run(snmp_router.read_snmp_route(request=request, user=None))

    request = type("Request", (), {"query_params": {"address": "1", "slave": "1"}})()
    with pytest.raises(HTTPException):
        asyncio.run(modbus_router.read_modbus(request=request, user=None))
