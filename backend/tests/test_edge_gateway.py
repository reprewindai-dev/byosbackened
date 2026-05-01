from __future__ import annotations

import asyncio
import pytest
from fastapi.routing import APIRoute
from fastapi import HTTPException

from types import SimpleNamespace

from edge.core import normalizer
from edge.core import pipeline
from edge.routers import modbus as modbus_router
from edge.routers import snmp as snmp_router
from edge.services.scheduler import SnmpPollTarget, ModbusPollTarget, poll_devices
from edge.routers import edge_ingest
from edge.services.legacy_targets import DemoTarget


def test_normalizer_casts_to_float_and_sets_fields():
    payload = normalizer.normalize("modbus", "device-1", "coil-1", "88")

    assert payload["protocol"] == "modbus"
    assert payload["source"] == "device-1"
    assert payload["metric"] == "coil-1"
    assert payload["value"] == 88.0
    assert isinstance(payload["timestamp"], str)
    assert payload["timestamp"].endswith("Z")
    assert payload["units"] is None
    assert payload["raw"] == {}
    assert payload["tags"] == {}


def test_normalizer_preserves_non_numeric_value():
    payload = normalizer.normalize("snmp", "router-1", "sysDescr", "router-os")
    assert payload["value"] == "router-os"


def test_process_pipeline_routes_modbus_value_threshold(monkeypatch):
    async def fake_route_message(msg):
        return {
            "route": "edge",
            "metadata": msg.metadata,
            "payload": msg.payload,
        }

    monkeypatch.setattr("edge.core.pipeline.route_message", fake_route_message)

    payload = normalizer.normalize("modbus", "device", "temperature", "92.0")
    result = asyncio.run(pipeline.process_pipeline(payload, SimpleNamespace(workspace_id="ws-1")))

    assert result["route"] == "edge"
    assert result["metadata"]["alert"] is True


def test_modbus_router_calls_pipeline_with_normalized_payload(monkeypatch):
    called = {}

    async def fake_process_pipeline(data, user):
        called["data"] = data
        called["user_id"] = user.id
        return {"ok": True}

    monkeypatch.setattr("edge.routers.modbus.process_pipeline", fake_process_pipeline)
    monkeypatch.setattr(
        "edge.routers.modbus._get_client",
        lambda: SimpleNamespace(read=lambda address, slave=1: 123),
    )

    result = asyncio.run(
        modbus_router.read_modbus(address=100, user=SimpleNamespace(id="user-1"))
    )

    assert result["ok"] is True
    assert called["data"]["protocol"] == "modbus"
    assert called["data"]["source"] == "device"
    assert called["data"]["metric"] == "100"
    assert called["data"]["value"] == 123.0
    assert called["user_id"] == "user-1"


def test_snmp_router_calls_pipeline_with_normalized_payload(monkeypatch):
    called = {}

    async def fake_process_pipeline(data, user):
        called["data"] = data
        called["user_id"] = user.id
        return {"ok": True}

    monkeypatch.setattr("edge.routers.snmp.process_pipeline", fake_process_pipeline)
    monkeypatch.setattr("edge.routers.snmp.read_snmp", lambda ip, oid: "77")

    result = asyncio.run(
        snmp_router.read_snmp_route(
            ip="8.8.8.8",
            oid="1.3.6.1.2.1.1.5.0",
            user=SimpleNamespace(id="user-2"),
        )
    )

    assert result["ok"] is True
    assert called["data"]["protocol"] == "snmp"
    assert called["data"]["source"] == "8.8.8.8"
    assert called["data"]["metric"] == "1.3.6.1.2.1.1.5.0"
    assert called["data"]["value"] == 77.0
    assert called["user_id"] == "user-2"


def test_route_paths_exposed():
    from apps.api.main import app
    paths = {(route.path, ",".join(sorted(route.methods or []))) for route in app.routes if isinstance(route, APIRoute)}
    assert ("/api/v1/edge/modbus", "GET") in paths
    assert ("/api/v1/edge/snmp", "GET") in paths
    assert ("/api/v1/edge/protocol/modbus", "GET") in paths
    assert ("/api/v1/edge/protocol/snmp", "GET") in paths
    assert ("/api/v1/edge/demo/summary", "GET") in paths
    assert ("/api/v1/edge/demo/infrastructure", "GET") in paths


def test_protocol_aliases_map_to_same_handler():
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


@pytest.mark.parametrize("live", [False, True])
def test_public_demo_infrastructure_live_toggle(monkeypatch, live):
    if live:
        target = DemoTarget(
            host="demo.pysnmp.com",
            oid="1.3.6.1.2.1.1.3.0",
            metric="sysUpTimeInstance",
            scenario="network",
            title="network",
            description="Network demo",
            source="demo.pysnmp.com",
            cost_estimate=40,
        )
        monkeypatch.setattr(
            "edge.routers.edge_ingest.resolve_demo_target_for_live",
            lambda scenario: target,
        )
        monkeypatch.setattr("edge.routers.edge_ingest.read_snmp", lambda ip, oid: "99")
    else:
        monkeypatch.setattr("edge.routers.edge_ingest.resolve_demo_target_for_live", lambda scenario: (_ for _ in ()).throw(AssertionError("should not resolve live target")))
        monkeypatch.setattr("edge.routers.edge_ingest.read_snmp", lambda ip, oid: (_ for _ in ()).throw(AssertionError("should not call live read")))

    result = asyncio.run(edge_ingest.demo_infrastructure(scenario="network", live=live))

    assert result["scenario"] == "network"
    assert result["live"] is live
    if not live:
        assert result["fallback"] is True
    else:
        assert result["status"] in {"ok", "degraded"}


def test_public_demo_live_true_uses_allowlisted_target(monkeypatch):
    target = DemoTarget(
        host="demo.pysnmp.com",
        oid="1.3.6.1.2.1.1.3.0",
        metric="sysUpTimeInstance",
        scenario="network",
        title="network",
        description="Network demo",
        source="demo.pysnmp.com",
        cost_estimate=40,
    )
    calls = {}

    def fake_resolve(scenario):
        calls["scenario"] = scenario
        return target

    def fake_read_snmp(host, oid):
        calls["host"] = host
        calls["oid"] = oid
        return "123"

    monkeypatch.setattr("edge.routers.edge_ingest.resolve_demo_target_for_live", fake_resolve)
    monkeypatch.setattr("edge.routers.edge_ingest.read_snmp", fake_read_snmp)

    result = asyncio.run(edge_ingest.demo_infrastructure(scenario="network", live=True))

    assert calls["scenario"] == "network"
    assert calls["host"] == "demo.pysnmp.com"
    assert calls["oid"] == target.oid
    assert result["fallback"] is False
    assert result["live"] is True


def test_invalid_ip_oid_is_rejected():
    with pytest.raises(HTTPException):
        asyncio.run(snmp_router.read_snmp_route(ip="not-a-host", oid="bad", user=None))


@pytest.mark.asyncio
async def test_scheduler_polls_targets_and_increments_counter(monkeypatch):
    events = []

    async def fake_process(event):
        events.append(event)

    class FakeModbusClient:
        def __init__(self, *args, **kwargs) -> None:
            self._value = 10.0

        def connect(self):
            return True

        def read_holding_registers(self, address: int, count: int = 1, slave: int = 1):
            class FakeResponse:
                isError = False
                registers = [10]

            return FakeResponse()

        def close(self):
            return None

    def fake_load_client(_self=None):
        return FakeModbusClient

    monkeypatch.setattr("edge.services.scheduler.ModbusClient._load_client", fake_load_client)
    monkeypatch.setattr("edge.services.scheduler.ModbusClient.read", lambda self, address, slave=1: 10.0)
    monkeypatch.setattr(
        "edge.services.scheduler.read_snmp",
        lambda ip, oid, community="public", port=161: "20.0",
    )

    class User:
        id = "ws-test"

    events_count = await poll_devices(
        user=User(),
        modbus_targets=[ModbusPollTarget(address=1, source="mock-modbus", slave=1)],
        snmp_targets=[SnmpPollTarget(ip="127.0.0.1", oid="1.3.6.1.2.1.1.5.0", source="mock-snmp")],
        iterations=1,
        modbus_port="/dev/ttyUSB0",
        on_result=lambda event: fake_process(event),
    )

    assert events_count == 2
    assert len(events) == 2
    assert events[0]["protocol"] == "modbus"
    assert events[1]["protocol"] == "snmp"
