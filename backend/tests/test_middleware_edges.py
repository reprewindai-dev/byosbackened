from __future__ import annotations

from apps.api.middleware.entitlement_check import EntitlementCheckMiddleware
from apps.api.middleware.token_deduction import DEFAULT_ENDPOINT_COSTS


def test_edge_entitlement_paths_requirements():
    middleware = EntitlementCheckMiddleware(app=None)  # type: ignore[arg-type]

    assert middleware._get_required_plan("POST", "/api/v1/edge/input/webhook") == "starter"
    assert middleware._get_required_plan("GET", "/api/v1/edge/snmp") == "pro"
    assert middleware._get_required_plan("GET", "/api/v1/edge/modbus") == "pro"
    assert middleware._get_required_plan("GET", "/api/v1/edge/protocol/snmp") == "pro"
    assert middleware._get_required_plan("GET", "/api/v1/edge/protocol/modbus") == "pro"


def test_edge_token_cost_policies_for_protocol_and_webhook():
    assert DEFAULT_ENDPOINT_COSTS["/api/v1/edge/input/webhook"] == 25
    assert DEFAULT_ENDPOINT_COSTS["/api/v1/edge/snmp"] == 40
    assert DEFAULT_ENDPOINT_COSTS["/api/v1/edge/modbus"] == 40
    assert DEFAULT_ENDPOINT_COSTS["/api/v1/edge/protocol/snmp"] == 40
    assert DEFAULT_ENDPOINT_COSTS["/api/v1/edge/protocol/modbus"] == 40

