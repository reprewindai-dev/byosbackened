"""Edge ingest endpoints."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request, status

from edge.connectors.http import normalize_http_payload
from edge.schemas.edge_message import EdgeMessage
from edge.services.edge_rules import apply_rules
from edge.services.edge_processor import process_edge_payload, process_edge_data
from edge.services.legacy_targets import (
    DEMO_SNMP_HOSTS,
    build_decision_response,
    resolve_demo_target_for_live,
    scenario_fallback_payload,
    scenario_signal,
    validate_public_scenario_query,
    demo_summary,
)

router = APIRouter(prefix="/edge", tags=["Edge"])


def read_snmp(host: str, oid: str):
    """Compatibility-safe SNMP read wrapper for tests and deployed images."""
    try:
        from edge.connectors.snmp_client import read_snmp as _read_snmp

        return _read_snmp(host, oid)
    except ModuleNotFoundError:
        from edge.routers.snmp import read_snmp as _read_snmp

        return _read_snmp(host, oid)


def _read_snmp_demo_value(host: str, oid: str):
    """Load SNMP reader in a compatibility-safe way (supports legacy images)."""
    try:
        from edge.connectors.snmp_client import SNMPReadError

        return read_snmp(host, oid), SNMPReadError
    except ModuleNotFoundError:
        from edge.routers.snmp import _load_snmp_client

        err_cls, _ = _load_snmp_client()
        return read_snmp(host, oid), err_cls


def _as_bool(value: bool | str | None, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    normalized = str(value).strip().lower()
    return normalized in {"1", "true", "yes", "on"}


def _demo_payload_envelope(
    *,
    scenario: str,
    live: bool,
    trace_id: str,
    fallback: bool,
    event: dict[str, Any],
    outcome: dict[str, Any],
    cost_estimate: int = 40,
    error_code: str | None = None,
    error: str | None = None,
) -> dict[str, Any]:
    protocol = str(event.get("protocol") or ("modbus" if scenario == "machine" else "snmp"))
    source = str(event.get("source") or "demo")
    signal = event.get("signal") if isinstance(event.get("signal"), dict) else scenario_signal(scenario)
    response = build_decision_response(
        scenario=scenario,
        live=live,
        fallback=fallback,
        protocol=protocol,
        source=source,
        signal=signal,
        public_demo=True,
        customer_route_cost_credits=None,
        raw={"source_event_type": "public_demo", "scenario": scenario},
        error_code=error_code,
        error=error,
    )
    response.update({
        "status": "degraded" if fallback else "ok",
        "trace_id": trace_id,
        "cost_estimate": cost_estimate,
        "normalized_event": event,
        "rule_outcome": outcome,
        "allowlist_hosts": list(DEMO_SNMP_HOSTS),
    })
    return response


@router.post("/input/webhook")
async def webhook_ingest(data: dict):
    """Webhook input adapter for edge payloads."""
    pipeline_result = await process_edge_data(data)
    payload = data.get("payload") if isinstance(data.get("payload"), dict) else data
    scenario = str(data.get("scenario_hint") or data.get("scenario") or "custom").lower()
    if scenario not in {"network", "machine"}:
        scenario = "custom"
    protocol = str(data.get("protocol") or "http")
    source = str(data.get("source") or data.get("device") or "webhook")
    signal = {
        key: value
        for key, value in payload.items()
        if isinstance(value, (int, float, str, bool)) and key not in {"source", "device", "protocol"}
    } or {"received": True}
    response = build_decision_response(
        scenario=scenario,
        live=True,
        fallback=False,
        protocol=protocol,
        source=source,
        signal=signal,
        public_demo=False,
        customer_route_cost_credits=25,
        raw={"pipeline_result": pipeline_result},
    )
    if isinstance(pipeline_result, dict):
        response.update(pipeline_result)
    return response


@router.post("/ingest")
async def ingest_edge(data: dict):
    """Generic edge ingest endpoint."""
    return await process_edge_data(data)


@router.post("/input/http")
async def ingest_http(data: dict):
    """HTTP input adapter that normalizes via connector before processing."""
    msg = normalize_http_payload(data)
    return await process_edge_payload(msg)


@router.post("/demo")
async def demo_ingest():
    """Simple demo payload for rapid integration testing."""
    sample_payload: dict = {
        "device": "sensor-1",
        "temperature": 92,
        "status": "critical",
    }
    sample_msg = EdgeMessage.normalize(sample_payload, source="sensor-1", protocol="http")
    return await process_edge_payload(sample_msg)


@router.get("/demo/summary")
async def demo_summary_route():
    """Public summary for demo scenarios and target availability."""
    return demo_summary()


@router.get("/demo/infrastructure")
async def demo_infrastructure(
    request: Request = None,
    scenario: str = Query(default="network"),
    live: bool | str = Query(default=False),
):
    """Run a public demo scenario in live or fallback mode."""
    trace_id = str(uuid.uuid4())
    if request is not None:
        allowed_query_params = {"scenario", "live"}
        unexpected_params = set(request.query_params.keys()) - allowed_query_params
        if unexpected_params:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported query parameter(s): {', '.join(sorted(unexpected_params))}",
            )

    try:
        scenario_id = validate_public_scenario_query(scenario)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    is_live = _as_bool(live, default=False)
    if not is_live:
        event = scenario_fallback_payload(scenario_id, trace_id=trace_id)
        msg = apply_rules(EdgeMessage.normalize(event, source="demo", protocol="snmp"))
        return _demo_payload_envelope(
            scenario=scenario_id,
            live=False,
            trace_id=trace_id,
            fallback=True,
            event=event,
            outcome=msg.metadata,
            cost_estimate=40,
        )

    try:
        target = resolve_demo_target_for_live(scenario_id)
        if scenario_id == "machine":
            raise RuntimeError("Public live Modbus target unavailable; using deterministic fallback")
        raw_value, _ = _read_snmp_demo_value(target.host, target.oid)
    except Exception as exc:
        event = scenario_fallback_payload(scenario_id, trace_id=trace_id)
        msg = apply_rules(EdgeMessage.normalize(event, source="demo", protocol="snmp"))
        return _demo_payload_envelope(
            scenario=scenario_id,
            live=True,
            trace_id=trace_id,
            fallback=True,
            event=event,
            outcome=msg.metadata,
            cost_estimate=40,
            error_code="live_read_failed",
            error=str(exc),
        )

    event = target.as_payload(raw_value)
    event["trace_id"] = trace_id
    event["signal"] = scenario_signal(scenario_id, raw_value=raw_value)
    msg = apply_rules(EdgeMessage.normalize(event, source=target.source, protocol="snmp"))
    return _demo_payload_envelope(
        scenario=scenario_id,
        live=True,
        trace_id=trace_id,
        fallback=False,
        event=event,
        outcome=msg.metadata,
        cost_estimate=target.cost_estimate,
    )
