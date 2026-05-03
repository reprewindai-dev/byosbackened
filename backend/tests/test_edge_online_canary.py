from __future__ import annotations

from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from apps.api.deps import require_admin
from apps.api.routers import edge_canary as edge_canary_router
from edge.services import protocol_canary


class DummyDB:
    def __init__(self):
        self.rows = []

    def add(self, row):
        self.rows.append(row)

    def commit(self):
        return None

    def refresh(self, row):
        return None

    def query(self, model):
        class _Query:
            def __init__(self, rows):
                self._rows = rows

            def order_by(self, *_args, **_kwargs):
                return self

            def first(self):
                return self._rows[-1] if self._rows else None

        return _Query(self.rows)


def _build_test_app() -> TestClient:
    app = FastAPI()
    app.include_router(edge_canary_router.router, prefix="/api/v1")
    app.dependency_overrides[require_admin] = lambda: SimpleNamespace(id="user-1", is_superuser=True)
    return TestClient(app)


def test_canary_routes_registered():
    from apps.api.main import app

    paths = {(route.path, ",".join(sorted(route.methods or []))) for route in app.routes if isinstance(route, APIRoute)}
    assert ("/api/v1/admin/edge/canary/run", "POST") in paths
    assert ("/api/v1/edge/canary/public", "GET") in paths


def test_admin_canary_requires_auth():
    app = FastAPI()
    app.include_router(edge_canary_router.router, prefix="/api/v1")
    client = TestClient(app)

    response = client.post("/api/v1/admin/edge/canary/run")
    assert response.status_code == 401


def test_admin_canary_rejects_query_param_override(monkeypatch):
    client = _build_test_app()
    monkeypatch.setattr(edge_canary_router, "run_protocol_canary", lambda: {"status": "ok", "generated_at": "2026-05-01T00:00:00Z", "checks": {}, "proof": {}})
    monkeypatch.setattr(edge_canary_router, "_store_report", lambda db, report: None)

    response = client.post("/api/v1/admin/edge/canary/run?target=evil")
    assert response.status_code == 400


def test_public_summary_does_not_run_live_calls(monkeypatch):
    client = _build_test_app()
    dummy_db = DummyDB()
    dummy_db.rows.append(
        SimpleNamespace(
            report_json={
                "status": "ok",
                "generated_at": "2026-05-01T00:00:00Z",
                "checks": {
                    "snmp": {"status": "passed", "normalized_ok": True, "decision_ok": True, "audit_ok": True, "cost_control_ok": True},
                    "modbus_tcp": {"status": "passed", "normalized_ok": True, "decision_ok": True, "audit_ok": True, "cost_control_ok": True},
                    "mqtt": {"status": "passed", "normalized_ok": True, "decision_ok": True, "audit_ok": True, "cost_control_ok": True},
                    "webhook": {"status": "passed", "normalized_ok": True, "decision_ok": True, "audit_ok": True, "cost_control_ok": True},
                },
                "proof": {"normalized": True, "decision": True, "audit": True, "cost_control": True},
            }
        )
    )
    monkeypatch.setattr(edge_canary_router, "run_protocol_canary", lambda: (_ for _ in ()).throw(AssertionError("should not run")))
    monkeypatch.setattr(edge_canary_router, "_load_latest_report", lambda db: dummy_db.rows[-1].report_json)

    response = client.get("/api/v1/edge/canary/public")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["checks"]["snmp"] == "passed"
    assert payload["proof"]["normalized"] is True


def test_snmp_success_sets_proof_flags():
    calls = []

    def fake_read(host, oid, community="public", port=161):
        calls.append((host, oid, community, port))
        return "demo"

    result = protocol_canary.run_snmp_canary_check(read_fn=fake_read, generated_at="2026-05-01T00:00:00Z")
    assert result["status"] == "passed"
    assert result["connect_ok"] is True
    assert result["read_ok"] is True
    assert result["normalized_ok"] is True
    assert result["decision_ok"] is True
    assert result["audit_ok"] is True
    assert result["cost_control_ok"] is True
    assert len(calls) == 2


def test_modbus_success_sets_proof_flags():
    class FakeClient:
        def __init__(self, host, port=502, timeout=4):
            self.host = host
            self.port = port
            self.timeout = timeout

        def read_holding_register(self, address, slave=1, count=1):
            assert self.host == "45.8.248.56"
            assert self.port == 502
            return 92.0

    result = protocol_canary.run_modbus_canary_check(client_factory=FakeClient, generated_at="2026-05-01T00:00:00Z")
    assert result["status"] == "passed"
    assert result["connect_ok"] is True
    assert result["read_ok"] is True
    assert result["normalized_ok"] is True
    assert result["decision_ok"] is True
    assert result["audit_ok"] is True
    assert result["cost_control_ok"] is True


def test_mqtt_success_sets_proof_flags_and_payload_is_safe():
    class FakeMQTTClient:
        def __init__(self, host, port=1883, timeout=4.0):
            self.host = host
            self.port = port
            self.timeout = timeout

        def publish_and_consume(self, topic, payload):
            assert self.host == "broker.emqx.io"
            assert self.port == 1883
            assert "secret" not in str(payload).lower()
            return {"publish_ok": True, "consume_ok": True, "consumed_payload": payload}

    result = protocol_canary.run_mqtt_canary_check(client_factory=FakeMQTTClient, generated_at="2026-05-01T00:00:00Z")
    assert result["status"] == "passed"
    assert result["publish_ok"] is True
    assert result["consume_ok"] is True
    assert result["normalized_ok"] is True
    assert result["decision_ok"] is True
    assert result["audit_ok"] is True
    assert result["cost_control_ok"] is True
    assert "secret" not in str(protocol_canary.build_public_mqtt_canary_payload()).lower()


def test_webhook_self_test_returns_governed_metadata():
    result = protocol_canary.run_webhook_canary_check(generated_at="2026-05-01T00:00:00Z")
    assert result["status"] == "passed"
    assert result["accepted"] is True
    assert result["normalized_ok"] is True
    assert result["decision_ok"] is True
    assert result["audit_ok"] is True
    assert result["cost_control_ok"] is True


def test_one_failed_protocol_degrades_and_continues(monkeypatch):
    monkeypatch.setattr(protocol_canary, "run_snmp_canary_check", lambda **kwargs: {"status": "failed", "target": "demo", "connect_ok": False, "read_ok": False, "publish_ok": False, "consume_ok": False, "accepted": False, "normalized_ok": False, "decision_ok": False, "audit_ok": False, "cost_control_ok": False, "duration_ms": 1, "error": "demo down"})
    monkeypatch.setattr(protocol_canary, "run_modbus_canary_check", lambda **kwargs: {"status": "passed", "target": "demo", "connect_ok": True, "read_ok": True, "publish_ok": False, "consume_ok": False, "accepted": False, "normalized_ok": True, "decision_ok": True, "audit_ok": True, "cost_control_ok": True, "duration_ms": 1, "error": None})
    monkeypatch.setattr(protocol_canary, "run_mqtt_canary_check", lambda **kwargs: {"status": "passed", "target": "demo", "connect_ok": True, "read_ok": False, "publish_ok": True, "consume_ok": True, "accepted": False, "normalized_ok": True, "decision_ok": True, "audit_ok": True, "cost_control_ok": True, "duration_ms": 1, "error": None})
    monkeypatch.setattr(protocol_canary, "run_webhook_canary_check", lambda **kwargs: {"status": "passed", "target": "demo", "connect_ok": False, "read_ok": False, "publish_ok": False, "consume_ok": False, "accepted": True, "normalized_ok": True, "decision_ok": True, "audit_ok": True, "cost_control_ok": True, "duration_ms": 1, "error": None})

    report = protocol_canary.run_protocol_canary(generated_at="2026-05-01T00:00:00Z")
    assert report["status"] == "degraded"
    assert report["checks"]["snmp"]["status"] == "failed"
    assert report["checks"]["modbus_tcp"]["status"] == "passed"


def test_public_summary_sanitizes_report():
    report = {
        "status": "ok",
        "generated_at": "2026-05-01T00:00:00Z",
        "checks": {
            "snmp": {"status": "passed", "host": "demo.pysnmp.com", "normalized_ok": True, "decision_ok": True, "audit_ok": True, "cost_control_ok": True},
            "modbus_tcp": {"status": "passed", "target": "45.8.248.56:502", "normalized_ok": True, "decision_ok": True, "audit_ok": True, "cost_control_ok": True},
            "mqtt": {"status": "passed", "topic": "veklom/demo/abc/machine", "normalized_ok": True, "decision_ok": True, "audit_ok": True, "cost_control_ok": True},
            "webhook": {"status": "passed", "payload": {"temperature_c": 92}, "normalized_ok": True, "decision_ok": True, "audit_ok": True, "cost_control_ok": True},
        },
        "proof": {"normalized": True, "decision": True, "audit": True, "cost_control": True},
    }

    summary = protocol_canary.public_canary_summary(report)
    assert summary == {
        "status": "ok",
        "last_checked_at": "2026-05-01T00:00:00Z",
        "checks": {
            "snmp": "passed",
            "modbus_tcp": "passed",
            "mqtt": "passed",
            "webhook": "passed",
        },
        "proof": {
            "normalized": True,
            "decision": True,
            "audit": True,
            "cost_control": True,
        },
    }
