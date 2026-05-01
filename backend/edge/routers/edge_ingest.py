"""Edge ingest endpoints."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Query

from edge.connectors.http import normalize_http_payload
from edge.connectors.snmp_client import SNMPReadError, read_snmp
from edge.schemas.edge_message import EdgeMessage
from edge.services.edge_rules import apply_rules
from edge.services.edge_processor import process_edge_payload, process_edge_data
from edge.services.legacy_targets import (
    DEMO_SNMP_HOSTS,
    resolve_demo_target_for_live,
    scenario_fallback_payload,
    validate_public_scenario_query,
    demo_summary,
)

router = APIRouter(prefix="/edge", tags=["Edge"])


def _as_bool(value: bool | str | None, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    normalized = str(value).strip().lower()
    return normalized in {"1", "true", "yes", "on"}


def _demo_payload_envelope(*, scenario: str, live: bool, trace_id: str, fallback: bool, event: dict[str, Any], outcome: dict[str, Any], cost_estimate: int = 40) -> dict[str, Any]:
    return {
        "status": "degraded" if fallback else "ok",
        "trace_id": trace_id,
        "scenario": scenario,
        "live": live,
        "fallback": fallback,
        "cost_estimate": cost_estimate,
        "normalized_event": event,
        "rule_outcome": outcome,
        "allowlist_hosts": list(DEMO_SNMP_HOSTS),
    }


@router.post("/input/webhook")
async def webhook_ingest(data: dict):
    """Webhook input adapter for edge payloads."""
    return await process_edge_data(data)


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
    scenario: str = Query(default="network"),
    live: bool | str = Query(default=False),
):
    """Run a public demo scenario in live or fallback mode."""
    trace_id = str(uuid.uuid4())
    try:
        scenario_id = validate_public_scenario_query(scenario)
    except ValueError as exc:
        return {
            "status": "degraded",
            "error_code": "invalid_scenario",
            "fallback": True,
            "trace_id": trace_id,
            "error": str(exc),
        }

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
        raw_value = read_snmp(target.host, target.oid)
    except (ValueError, SNMPReadError) as exc:
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
        ) | {"status": "degraded", "error_code": "live_read_failed", "error": str(exc)}

    event = target.as_payload(raw_value)
    event["trace_id"] = trace_id
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
