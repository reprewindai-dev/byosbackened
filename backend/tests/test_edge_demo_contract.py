from __future__ import annotations

import re

from fastapi.testclient import TestClient

from apps.api.main import app


client = TestClient(app)


def _assert_contract(payload: dict, *, scenario: str, protocol: str, billable: bool) -> None:
    assert payload["scenario"] == scenario
    assert payload["protocol"] == protocol
    assert isinstance(payload["live"], bool)
    assert isinstance(payload["fallback"], bool)
    assert payload["source"]

    assert isinstance(payload["normalized"], list)
    assert payload["normalized"]
    first = payload["normalized"][0]
    assert set(first) == {"protocol", "source", "metric", "value", "units", "timestamp", "raw", "tags"}
    assert first["protocol"] == protocol
    assert first["timestamp"].endswith("Z")

    decision = payload["decision"]
    assert decision["severity"] in {"normal", "warning", "critical"}
    assert decision["action"] in {"investigate", "reduce_load", "notify", "block_unsafe_action"}
    assert isinstance(decision["summary"], str)
    assert isinstance(decision["likely_causes"], list)
    assert isinstance(decision["recommended_actions"], list)
    assert isinstance(decision["blocked_actions"], list)

    assert payload["trace"] == [
        "legacy_ingest",
        "normalize",
        "policy_control",
        "decision",
        "audit_ready",
    ]
    assert re.fullmatch(r"[0-9a-f]{64}", payload["audit"]["proof_hash"])
    assert payload["audit"]["replayable"] is True
    assert payload["audit"]["generated_at"].endswith("Z")
    assert payload["cost_control"]["billable"] is billable


def test_demo_summary_public_200():
    response = client.get("/api/v1/edge/demo/summary")
    assert response.status_code == 200
    payload = response.json()
    assert payload["available"] is True
    assert {item["id"] for item in payload["scenarios"]} == {"network", "machine"}


def test_network_demo_live_false_contract():
    response = client.get("/api/v1/edge/demo/infrastructure?scenario=network&live=false")
    assert response.status_code == 200
    payload = response.json()
    _assert_contract(payload, scenario="network", protocol="snmp", billable=False)
    assert payload["decision"]["severity"] == "critical"
    assert payload["decision"]["action"] == "investigate"
    assert payload["fallback"] is True
    metrics = {item["metric"]: item["value"] for item in payload["normalized"]}
    assert metrics["retransmissions"] == 16
    assert metrics["rto_ms"] == 5000


def test_machine_demo_live_false_contract():
    response = client.get("/api/v1/edge/demo/infrastructure?scenario=machine&live=false")
    assert response.status_code == 200
    payload = response.json()
    _assert_contract(payload, scenario="machine", protocol="modbus", billable=False)
    assert payload["decision"]["severity"] == "critical"
    assert payload["decision"]["action"] == "reduce_load"
    metrics = {item["metric"]: item["value"] for item in payload["normalized"]}
    assert metrics["temperature_c"] == 92
    assert metrics["vibration_index"] == 71


def test_public_demo_rejects_unknown_scenario():
    response = client.get("/api/v1/edge/demo/infrastructure?scenario=unknown&live=false")
    assert response.status_code == 400


def test_public_demo_rejects_arbitrary_target_params():
    response = client.get(
        "/api/v1/edge/demo/infrastructure?scenario=network&live=false&ip=127.0.0.1"
    )
    assert response.status_code == 400


def test_protocol_routes_protected_without_auth():
    assert client.get("/api/v1/edge/protocol/snmp").status_code == 401
    assert client.get("/api/v1/edge/protocol/modbus").status_code == 401

