from __future__ import annotations

import asyncio
import hashlib
from types import SimpleNamespace

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from apps.api.main import app
from apps.api.routers import auth, internal_operators


def test_internal_operator_routes_are_registered():
    paths = {route.path for route in app.routes if isinstance(route, APIRoute)}

    assert "/api/v1/internal/operators/overview" in paths
    assert "/api/v1/internal/operators/registry" in paths
    assert "/api/v1/internal/operators/workers" in paths
    assert "/api/v1/internal/operators/runs" in paths
    assert "/api/v1/internal/operators/digest" in paths
    assert "/api/v1/internal/operators/watch" in paths
    assert "/api/v1/internal/operators/workers/{worker_id}/heartbeat" in paths


def test_internal_operator_overview_requires_auth():
    client = TestClient(app)

    response = client.get("/api/v1/internal/operators/overview")

    assert response.status_code == 401


def test_operator_watch_uses_global_scope(monkeypatch):
    calls = []

    def fake_evaluate_operator_watch(db, *, workspace_id=None, persist=True):
        calls.append({"workspace_id": workspace_id, "persist": persist})
        return {"status": "healthy", "workspace_id": workspace_id}

    monkeypatch.setattr(internal_operators, "evaluate_operator_watch", fake_evaluate_operator_watch)
    principal = internal_operators.OperatorPrincipal(
        workspace_id="operator-workspace",
        user_id="operator-user",
        principal_type="automation_key",
    )

    asyncio.run(internal_operators.operator_digest(principal=principal, db=object()))
    asyncio.run(internal_operators.operator_watch(principal=principal, db=object()))

    assert calls == [
        {"workspace_id": None, "persist": False},
        {"workspace_id": None, "persist": True},
    ]


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
        "builder-scout",
        "builder-forge",
        "builder-arbiter",
        "sentinel",
        "mirror",
        "polish",
        "glide",
        "pulse",
        "sheriff",
        "welcome",
    }

    assert expected.issubset(internal_operators.WORKER_REGISTRY)
    assert set(internal_operators.MINIMUM_LIVE_SET) == {
        "gauge",
        "ledger",
        "sentinel",
        "mirror",
        "pulse",
        "sheriff",
        "polish",
    }
    for worker_id, worker in internal_operators.WORKER_REGISTRY.items():
        payload = internal_operators._worker_payload(worker_id, worker)
        assert payload["customer_visible"] is False
        assert payload["ships_to_buyer_package"] is False
        assert payload["mission"]
        assert payload["hard_kpis"]
        assert payload["primary_pillar"]
        assert payload["committees"]
        assert payload["trigger"]
        assert payload["inputs"]
        assert payload["outputs"]
        assert payload["success_metric"]
        assert payload["escalation"]
        assert payload["rollout_stage"] in {"ready", "staged", "minimum_live"}


def test_worker_committees_are_resolved():
    assert set(internal_operators._worker_committees("sheriff")) == {
        "governance-evidence",
        "experience-assurance",
    }
    assert set(internal_operators._worker_committees("welcome")) == {
        "growth-intelligence",
        "experience-assurance",
    }


def test_committee_payload_contains_readiness_summary():
    payload = internal_operators._committee_payload(
        "experience-assurance",
        internal_operators.COMMITTEE_REGISTRY["experience-assurance"],
    )

    assert payload["name"] == "Experience Assurance Committee"
    assert "sentinel" in payload["worker_ids"]
    assert "mirror" in payload["worker_ids"]
    assert payload["ready_workers"] >= 1


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


def test_customer_api_key_scopes_are_normalized_to_tenant_safe_values():
    user = SimpleNamespace(is_superuser=False)

    assert auth._normalize_api_key_scopes(["read", "EXEC", "read", "write"], user) == ["READ", "EXEC", "WRITE"]


def test_customer_api_key_scopes_block_internal_operator_scopes():
    user = SimpleNamespace(is_superuser=False)

    with pytest.raises(Exception) as exc_info:
        auth._normalize_api_key_scopes(["read", "automation"], user)

    assert getattr(exc_info.value, "status_code", None) == 403


def test_superuser_can_create_internal_operator_api_key_scopes():
    user = SimpleNamespace(is_superuser=True)

    assert auth._normalize_api_key_scopes(["automation", "admin"], user) == ["AUTOMATION", "ADMIN"]


def test_superuser_can_create_purpose_specific_worker_api_key_scopes():
    user = SimpleNamespace(is_superuser=True)

    assert auth._normalize_api_key_scopes(["marketplace_automation", "job_processor"], user) == [
        "MARKETPLACE_AUTOMATION",
        "JOB_PROCESSOR",
    ]


def test_customer_cannot_create_purpose_specific_worker_api_key_scopes():
    user = SimpleNamespace(is_superuser=False)

    with pytest.raises(Exception) as exc_info:
        auth._normalize_api_key_scopes(["marketplace_automation"], user)

    assert getattr(exc_info.value, "status_code", None) == 403


def test_internal_operator_api_key_owner_must_be_active_superuser():
    api_key = SimpleNamespace(workspace_id="operator-workspace")
    customer_owner = SimpleNamespace(
        workspace_id="operator-workspace",
        is_superuser=False,
        is_active=True,
        status="active",
    )
    platform_owner = SimpleNamespace(
        workspace_id="operator-workspace",
        is_superuser=True,
        is_active=True,
        status="active",
    )
    wrong_workspace_owner = SimpleNamespace(
        workspace_id="customer-workspace",
        is_superuser=True,
        is_active=True,
        status="active",
    )
    suspended_owner = SimpleNamespace(
        workspace_id="operator-workspace",
        is_superuser=True,
        is_active=True,
        status="suspended",
    )

    assert internal_operators._is_active_superuser_key_owner(customer_owner, api_key) is False
    assert internal_operators._is_active_superuser_key_owner(platform_owner, api_key) is True
    assert internal_operators._is_active_superuser_key_owner(wrong_workspace_owner, api_key) is False
    assert internal_operators._is_active_superuser_key_owner(suspended_owner, api_key) is False


def test_customer_owned_admin_scope_key_cannot_open_internal_operator_routes():
    raw_token = "byos_customer_admin_scope"
    api_key = SimpleNamespace(
        key_hash=hashlib.sha256(raw_token.encode()).hexdigest(),
        is_active=True,
        expires_at=None,
        scopes=["ADMIN"],
        workspace_id="customer-workspace",
        user_id="customer-user",
    )
    customer_owner = SimpleNamespace(
        id="customer-user",
        workspace_id="customer-workspace",
        is_superuser=False,
        is_active=True,
        status="active",
    )

    class FakeQuery:
        def __init__(self, result):
            self.result = result

        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return self.result

    class FakeDB:
        def query(self, model):
            if model is internal_operators.APIKey:
                return FakeQuery(api_key)
            if model is internal_operators.User:
                return FakeQuery(customer_owner)
            return FakeQuery(None)

    request = SimpleNamespace(state=SimpleNamespace(is_superuser=False))

    with pytest.raises(Exception) as exc_info:
        asyncio.run(
            internal_operators.require_internal_operator(
                request,
                authorization=f"Bearer {raw_token}",
                db=FakeDB(),
            )
        )

    assert getattr(exc_info.value, "status_code", None) == 403
    assert getattr(exc_info.value, "detail", "") == "Superuser automation key required"
