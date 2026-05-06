from __future__ import annotations

from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from apps.api.main import app
from apps.api.routers import internal_operators


def test_internal_operator_routes_are_registered():
    paths = {route.path for route in app.routes if isinstance(route, APIRoute)}

    assert "/api/v1/internal/operators/overview" in paths
    assert "/api/v1/internal/operators/workers" in paths
    assert "/api/v1/internal/operators/runs" in paths
    assert "/api/v1/internal/operators/workers/{worker_id}/heartbeat" in paths


def test_internal_operator_overview_requires_auth():
    client = TestClient(app)

    response = client.get("/api/v1/internal/operators/overview")

    assert response.status_code == 401


def test_worker_registry_is_internal_only():
    expected = {
        "herald",
        "harvest",
        "bouncer",
        "gauge",
        "ledger",
        "signal",
        "oracle",
        "mint",
        "scout",
        "arbiter",
    }

    assert expected.issubset(internal_operators.WORKER_REGISTRY)
    for worker_id, worker in internal_operators.WORKER_REGISTRY.items():
        payload = internal_operators._worker_payload(worker_id, worker)
        assert payload["customer_visible"] is False
        assert payload["ships_to_buyer_package"] is False
        assert payload["mission"]
        assert payload["hard_kpis"]


def test_internal_operator_details_redact_secret_like_fields():
    value = {
        "safe": "ok",
        "api_key": "should-not-leak",
        "nested": {"token": "also-secret", "public": "fine"},
        "list": [{"password": "hidden"}],
    }

    assert internal_operators._redact_details(value) == {
        "safe": "ok",
        "api_key": "[redacted]",
        "nested": {"token": "[redacted]", "public": "fine"},
        "list": [{"password": "[redacted]"}],
    }


def test_internal_operator_details_size_is_bounded():
    oversized = {"payload": "x" * (internal_operators.MAX_DETAILS_BYTES + 1)}

    try:
        internal_operators._safe_details_json(oversized)
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 413
    else:
        raise AssertionError("oversized internal operator details should fail closed")
