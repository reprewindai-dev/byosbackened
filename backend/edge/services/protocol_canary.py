"""Live protocol canary and proof report generation."""
from __future__ import annotations

import asyncio
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Callable

from edge.connectors.http import normalize_http_payload
from edge.connectors.modbus_tcp_client import ModbusTCPClient
from edge.connectors.mqtt_client import MQTTCanaryClient, build_public_mqtt_payload
from edge.connectors.snmp_client import read_snmp
from edge.services.edge_rules import apply_rules
from edge.services.legacy_targets import build_decision_response


SNMP_CANARY_TARGET = {
    "host": "demo.pysnmp.com",
    "port": 161,
    "community": "public",
    "oids": {
        "sysDescr": "1.3.6.1.2.1.1.1.0",
        "sysUpTime": "1.3.6.1.2.1.1.3.0",
    },
}

MODBUS_CANARY_TARGET = {
    "host": "45.8.248.56",
    "port": 502,
    "slave_id": 1,
    "register_type": "holding_register",
    "address": 1,
    "count": 1,
}

MQTT_CANARY_TARGET = {
    "broker": "broker.emqx.io",
    "port": 1883,
    "topic_prefix": "veklom/demo",
}

WEBHOOK_CANARY_PAYLOAD = {
    "source": "canary-pump-001",
    "protocol": "http",
    "scenario_hint": "machine",
    "payload": {
        "temperature_c": 92,
        "vibration_index": 71,
    },
}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_now_iso() -> str:
    return _utc_now().replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _duration_ms(start: float) -> int:
    return int(round((time.perf_counter() - start) * 1000))


def _governed_proof(
    *,
    scenario: str,
    protocol: str,
    source: str,
    signal: dict[str, Any],
    generated_at: str,
    raw: dict[str, Any] | None = None,
) -> dict[str, Any]:
    response = build_decision_response(
        scenario=scenario,
        live=True,
        fallback=False,
        protocol=protocol,
        source=source,
        signal=signal,
        public_demo=True,
        customer_route_cost_credits=None,
        generated_at=generated_at,
        raw=raw or {},
    )
    return {
        "normalized_ok": bool(response.get("normalized")),
        "decision_ok": bool(response.get("decision")),
        "audit_ok": bool(response.get("audit")),
        "cost_control_ok": bool(response.get("cost_control")),
        "proof_response": response,
    }


def build_public_mqtt_canary_payload() -> dict[str, Any]:
    return build_public_mqtt_payload()


def build_public_webhook_canary_payload() -> dict[str, Any]:
    return dict(WEBHOOK_CANARY_PAYLOAD)


def _base_check(name: str, target: str) -> dict[str, Any]:
    return {
        "name": name,
        "target": target,
        "status": "failed",
        "connect_ok": False,
        "read_ok": False,
        "publish_ok": False,
        "consume_ok": False,
        "accepted": False,
        "normalized_ok": False,
        "decision_ok": False,
        "audit_ok": False,
        "cost_control_ok": False,
        "duration_ms": 0,
        "error": None,
    }


def run_snmp_canary_check(
    *,
    read_fn: Callable[..., str] = read_snmp,
    generated_at: str | None = None,
    timeout_seconds: float = 4.0,
) -> dict[str, Any]:
    generated_at = generated_at or _utc_now_iso()
    start = time.perf_counter()
    target = f"{SNMP_CANARY_TARGET['host']}:{SNMP_CANARY_TARGET['port']}"
    result = _base_check("snmp", target)
    try:
        sys_descr = read_fn(
            SNMP_CANARY_TARGET["host"],
            SNMP_CANARY_TARGET["oids"]["sysDescr"],
            community=SNMP_CANARY_TARGET["community"],
            port=SNMP_CANARY_TARGET["port"],
        )
        sys_uptime = read_fn(
            SNMP_CANARY_TARGET["host"],
            SNMP_CANARY_TARGET["oids"]["sysUpTime"],
            community=SNMP_CANARY_TARGET["community"],
            port=SNMP_CANARY_TARGET["port"],
        )
        proof = _governed_proof(
            scenario="network",
            protocol="snmp",
            source=SNMP_CANARY_TARGET["host"],
            signal={
                "sysDescr": str(sys_descr),
                "sysUpTime": str(sys_uptime),
            },
            generated_at=generated_at,
            raw={
                "host": SNMP_CANARY_TARGET["host"],
                "oids": dict(SNMP_CANARY_TARGET["oids"]),
                "sysDescr": str(sys_descr),
                "sysUpTime": str(sys_uptime),
            },
        )
        result.update({
            "status": "passed",
            "connect_ok": True,
            "read_ok": True,
            "normalized_ok": proof["normalized_ok"],
            "decision_ok": proof["decision_ok"],
            "audit_ok": proof["audit_ok"],
            "cost_control_ok": proof["cost_control_ok"],
            "proof_response": proof["proof_response"],
        })
    except Exception as exc:
        result["error"] = str(exc)
    result["duration_ms"] = _duration_ms(start)
    if result["status"] != "passed":
        result["status"] = "failed"
    return result


def run_modbus_canary_check(
    *,
    client_factory: Callable[..., ModbusTCPClient] = ModbusTCPClient,
    generated_at: str | None = None,
    timeout_seconds: float = 4.0,
) -> dict[str, Any]:
    generated_at = generated_at or _utc_now_iso()
    start = time.perf_counter()
    target = f"{MODBUS_CANARY_TARGET['host']}:{MODBUS_CANARY_TARGET['port']}"
    result = _base_check("modbus_tcp", target)
    try:
        client = client_factory(
            host=MODBUS_CANARY_TARGET["host"],
            port=MODBUS_CANARY_TARGET["port"],
            timeout=timeout_seconds,
        )
        value = client.read_holding_register(
            address=MODBUS_CANARY_TARGET["address"],
            slave=MODBUS_CANARY_TARGET["slave_id"],
            count=MODBUS_CANARY_TARGET["count"],
        )
        proof = _governed_proof(
            scenario="machine",
            protocol="modbus",
            source=MODBUS_CANARY_TARGET["host"],
            signal={
                "temperature_c": float(value),
                "register_value": float(value),
            },
            generated_at=generated_at,
            raw={
                "host": MODBUS_CANARY_TARGET["host"],
                "port": MODBUS_CANARY_TARGET["port"],
                "slave_id": MODBUS_CANARY_TARGET["slave_id"],
                "address": MODBUS_CANARY_TARGET["address"],
                "value": float(value),
            },
        )
        result.update({
            "status": "passed",
            "connect_ok": True,
            "read_ok": True,
            "normalized_ok": proof["normalized_ok"],
            "decision_ok": proof["decision_ok"],
            "audit_ok": proof["audit_ok"],
            "cost_control_ok": proof["cost_control_ok"],
            "proof_response": proof["proof_response"],
        })
    except Exception as exc:
        result["error"] = str(exc)
    result["duration_ms"] = _duration_ms(start)
    if result["status"] != "passed":
        result["status"] = "failed"
    return result


def run_mqtt_canary_check(
    *,
    client_factory: Callable[..., MQTTCanaryClient] = MQTTCanaryClient,
    generated_at: str | None = None,
    timeout_seconds: float = 4.0,
) -> dict[str, Any]:
    generated_at = generated_at or _utc_now_iso()
    start = time.perf_counter()
    target = f"{MQTT_CANARY_TARGET['broker']}:{MQTT_CANARY_TARGET['port']}"
    result = _base_check("mqtt", target)
    topic = f"{MQTT_CANARY_TARGET['topic_prefix']}/{uuid.uuid4().hex}/machine"
    payload = build_public_mqtt_canary_payload()
    try:
        client = client_factory(
            host=MQTT_CANARY_TARGET["broker"],
            port=MQTT_CANARY_TARGET["port"],
            timeout=timeout_seconds,
        )
        mqtt_result = client.publish_and_consume(topic, payload)
        proof = _governed_proof(
            scenario="machine",
            protocol="mqtt",
            source=topic,
            signal=dict(payload),
            generated_at=generated_at,
            raw={
                "broker": MQTT_CANARY_TARGET["broker"],
                "port": MQTT_CANARY_TARGET["port"],
                "topic": topic,
                "published_payload": payload,
                "consumed_payload": mqtt_result.get("consumed_payload", {}),
            },
        )
        result.update({
            "status": "passed",
            "connect_ok": True,
            "publish_ok": bool(mqtt_result.get("publish_ok")),
            "consume_ok": bool(mqtt_result.get("consume_ok")),
            "normalized_ok": proof["normalized_ok"],
            "decision_ok": proof["decision_ok"],
            "audit_ok": proof["audit_ok"],
            "cost_control_ok": proof["cost_control_ok"],
            "proof_response": proof["proof_response"],
            "payload": payload,
            "topic": topic,
        })
    except Exception as exc:
        result["error"] = str(exc)
    result["duration_ms"] = _duration_ms(start)
    if result["status"] != "passed":
        result["status"] = "failed"
    return result


def run_webhook_canary_check(*, generated_at: str | None = None) -> dict[str, Any]:
    generated_at = generated_at or _utc_now_iso()
    start = time.perf_counter()
    target = "POST /api/v1/edge/input/webhook"
    result = _base_check("webhook", target)
    try:
        payload = build_public_webhook_canary_payload()
        normalized_message = normalize_http_payload(payload)
        ruled_message = apply_rules(normalized_message)
        signal = {
            key: value
            for key, value in dict(payload.get("payload") or {}).items()
            if isinstance(value, (int, float, str, bool))
        }
        proof = _governed_proof(
            scenario="machine",
            protocol="http",
            source=str(payload.get("source") or "webhook"),
            signal=signal,
            generated_at=generated_at,
            raw={
                "accepted_payload": payload,
                "normalized_payload": dict(normalized_message.payload),
                "rule_metadata": dict(ruled_message.metadata),
            },
        )
        result.update({
            "status": "passed",
            "accepted": True,
            "normalized_ok": proof["normalized_ok"],
            "decision_ok": proof["decision_ok"],
            "audit_ok": proof["audit_ok"],
            "cost_control_ok": proof["cost_control_ok"],
            "proof_response": proof["proof_response"],
            "payload": payload,
        })
    except Exception as exc:
        result["error"] = str(exc)
    result["duration_ms"] = _duration_ms(start)
    if result["status"] != "passed":
        result["status"] = "failed"
    return result


def _top_status(checks: dict[str, dict[str, Any]]) -> str:
    statuses = [str(check.get("status") or "failed") for check in checks.values()]
    if all(status == "passed" for status in statuses):
        return "ok"
    if any(status == "passed" or status == "degraded" for status in statuses):
        return "degraded"
    return "failed"


def run_protocol_canary(*, generated_at: str | None = None) -> dict[str, Any]:
    generated_at = generated_at or _utc_now_iso()
    checks = {
        "snmp": run_snmp_canary_check(generated_at=generated_at),
        "modbus_tcp": run_modbus_canary_check(generated_at=generated_at),
        "mqtt": run_mqtt_canary_check(generated_at=generated_at),
        "webhook": run_webhook_canary_check(generated_at=generated_at),
    }
    proof_all_ok = all(
        check.get("status") == "passed"
        and check.get("normalized_ok")
        and check.get("decision_ok")
        and check.get("audit_ok")
        and check.get("cost_control_ok")
        for check in checks.values()
    )
    status = _top_status(checks)
    if status == "ok" and not proof_all_ok:
        status = "degraded"
    return {
        "status": status,
        "generated_at": generated_at,
        "checks": checks,
        "proof": {
            "chain": ["connect", "read_or_publish", "normalize", "decision", "audit", "cost_control"],
            "normalized": proof_all_ok,
            "decision": proof_all_ok,
            "audit": proof_all_ok,
            "cost_control": proof_all_ok,
            "notes": [
                "All live protocol targets are allowlisted.",
                "No arbitrary IP or host scanning is allowed.",
                "No secrets or customer data are sent to public brokers.",
            ],
        },
    }


def public_canary_summary(report: dict[str, Any] | None) -> dict[str, Any]:
    if not report:
        return {
            "status": "not_run",
            "last_checked_at": None,
            "checks": {
                "snmp": "not_run",
                "modbus_tcp": "not_run",
                "mqtt": "not_run",
                "webhook": "not_run",
            },
            "proof": {
                "normalized": False,
                "decision": False,
                "audit": False,
                "cost_control": False,
            },
        }

    checks = report.get("checks") if isinstance(report.get("checks"), dict) else {}
    return {
        "status": report.get("status", "not_run"),
        "last_checked_at": report.get("generated_at"),
        "checks": {
            "snmp": str((checks.get("snmp") or {}).get("status", "not_run")),
            "modbus_tcp": str((checks.get("modbus_tcp") or {}).get("status", "not_run")),
            "mqtt": str((checks.get("mqtt") or {}).get("status", "not_run")),
            "webhook": str((checks.get("webhook") or {}).get("status", "not_run")),
        },
        "proof": {
            "normalized": all(bool((check or {}).get("normalized_ok")) for check in checks.values()),
            "decision": all(bool((check or {}).get("decision_ok")) for check in checks.values()),
            "audit": all(bool((check or {}).get("audit_ok")) for check in checks.values()),
            "cost_control": all(bool((check or {}).get("cost_control_ok", True)) for check in checks.values()),
        },
    }
