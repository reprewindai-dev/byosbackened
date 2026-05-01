"""Shared legacy demo targets and scenario presets."""

from __future__ import annotations

import ipaddress
import socket
import uuid
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse


DEMO_SNMP_HOSTS = ("demo.pysnmp.com", "demo.snmplabs.com")

SCENARIO_PRESETS = {
    "network": {
        "title": "network",
        "description": "Core network control-plane checks (SNMP demo)",
        "oid": "1.3.6.1.2.1.1.3.0",
        "metric": "sysUpTimeInstance",
        "fallback_payload": {
            "protocol": "snmp",
            "source": "demo.pysnmp.com",
            "metric": "sysUpTimeInstance",
            "value": 999999.0,
        },
        "cost_estimate": 40,
    },
    "machine": {
        "title": "machine",
        "description": "Machine telemetry control demo (SNMP readback)",
        "oid": "1.3.6.1.2.1.1.1.0",
        "metric": "sysDescr",
        "fallback_payload": {
            "protocol": "snmp",
            "source": "demo.pysnmp.com",
            "metric": "sysDescr",
            "value": 42.0,
        },
        "cost_estimate": 40,
    },
}


@dataclass(frozen=True)
class DemoTarget:
    host: str
    oid: str
    metric: str
    scenario: str
    title: str
    description: str
    source: str
    cost_estimate: int

    def as_payload(self, value: float | int | str) -> dict[str, Any]:
        return {
            "protocol": "snmp",
            "source": self.source,
            "metric": self.metric,
            "value": float(value),
            "scenario": self.scenario,
            "metric_oid": self.oid,
            "trace_id": str(uuid.uuid4()),
        }


def _normalise_host(host: str) -> str:
    return (host or "").strip().lower()


def is_allowed_host(host: str) -> bool:
    host = _normalise_host(host)
    if host in DEMO_SNMP_HOSTS:
        return True
    return False


def resolve_demo_target(scenario: str, *, live: bool) -> DemoTarget:
    preset = SCENARIO_PRESETS.get(scenario)
    if not preset:
        raise ValueError("Unsupported scenario")

    host = DEMO_SNMP_HOSTS[0]
    return DemoTarget(
        host=host,
        oid=str(preset["oid"]),
        metric=str(preset["metric"]),
        scenario=scenario,
        title=str(preset["title"]),
        description=str(preset["description"]),
        source=host,
        cost_estimate=int(preset["cost_estimate"]),
    )


def resolve_demo_target_for_live(scenario: str, *, host: str | None = None, oid: str | None = None) -> DemoTarget:
    """Resolve and validate a live public demo target."""
    scenario = validate_public_scenario_query(scenario)
    if host is None:
        host = DEMO_SNMP_HOSTS[0]
    normalized_host = _normalise_host(host)
    enforce_live_target_allowlist(normalized_host, str(oid or SCENARIO_PRESETS[scenario]["oid"]))
    preset = SCENARIO_PRESETS[scenario]
    return DemoTarget(
        host=normalized_host,
        oid=str(oid or preset["oid"]),
        metric=str(preset["metric"]),
        scenario=scenario,
        title=str(preset["title"]),
        description=str(preset["description"]),
        source=normalized_host,
        cost_estimate=int(preset["cost_estimate"]),
    )


def scenario_fallback_payload(scenario: str, *, trace_id: str | None = None) -> dict[str, Any]:
    preset = SCENARIO_PRESETS.get(scenario)
    if not preset:
        raise ValueError("Unsupported scenario")
    payload: dict[str, Any] = dict(preset["fallback_payload"])
    payload["scenario"] = scenario
    payload["trace_id"] = trace_id or str(uuid.uuid4())
    payload["fallback"] = True
    return payload


def validate_public_scenario_query(scenario: str) -> str:
    normalized = (scenario or "").strip().lower()
    if normalized not in SCENARIO_PRESETS:
        raise ValueError("Invalid scenario")
    return normalized


def demo_summary() -> dict[str, Any]:
    return {
        "available": True,
        "scenarios": [
            {
                "id": key,
                "title": value["title"],
                "description": value["description"],
                "metric": value["metric"],
                "oid": value["oid"],
                "cost_estimate": value["cost_estimate"],
            }
            for key, value in SCENARIO_PRESETS.items()
        ],
        "targets": {
            "snmp": {
                "hosts": list(DEMO_SNMP_HOSTS),
                "public_live_mode": "allowlisted",
            }
        },
    }


def validate_ip_or_hostname(target: str) -> tuple[str, str]:
    """Return (normalized_target, target_type) if safe."""
    if not target:
        raise ValueError("ip_or_host is required")

    candidate = _normalise_host(target)
    if candidate.startswith("http://") or candidate.startswith("https://"):
        parsed = urlparse(candidate)
        if parsed.hostname:
            candidate = parsed.hostname

    try:
        ip = ipaddress.ip_address(candidate)
        if ip.version == 4 and ip.is_private:
            raise ValueError("private IPv4 addresses are not allowed")
        if ip.version == 6 and ip.is_private:
            raise ValueError("private IPv6 addresses are not allowed")
        return str(ip), "ip"
    except ValueError:
        pass

    # hostnames are accepted only for allowlisted allowlist checks
    if all(part.isdigit() for part in candidate.split(".")):
        raise ValueError("invalid ip format")

    if not all(part.replace("-", "").replace(".", "").isalnum() or part in {"-", "."} for part in candidate):
        raise ValueError("invalid hostname format")

    return candidate, "host"


def enforce_live_target_allowlist(host: str, oid: str) -> None:
    host = _normalise_host(host)
    if not is_allowed_host(host):
        raise ValueError("target host is not allowlisted")
    if not is_valid_oid(oid):
        raise ValueError("invalid OID format")


def is_private_or_local_host(host: str) -> bool:
    """Return True when host resolves to private or loopback ranges."""
    candidate = _normalise_host(host)
    ip = None
    try:
        ip = ipaddress.ip_address(candidate)
    except ValueError:
        return False

    return ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved


def validate_snmp_input_for_demo_request(host: str, oid: str) -> tuple[str, str]:
    """Validate user-provided SNMP input for public demo requests."""
    host, host_type = validate_ip_or_hostname(host)
    if host_type == "ip":
        if is_private_or_local_host(host):
            raise ValueError("private or local IPs are not allowed")
    elif host_type == "host" and not is_allowed_host(host):
        raise ValueError("target host is not allowlisted")
    if not is_valid_oid(oid):
        raise ValueError("invalid OID format")
    return host, host_type


def validate_snmp_input_for_gateway(host: str, oid: str) -> tuple[str, str]:
    """Validate user-provided SNMP input for authenticated protocol routes."""
    host, host_type = validate_ip_or_hostname(host)
    if not is_valid_oid(oid):
        raise ValueError("invalid OID format")
    # Explicitly block obvious unsafe private/reserved/routable local IPs.
    if host_type == "ip" and is_private_or_local_host(host):
        raise ValueError("private or local IPs are not allowed")
    return host, host_type


def is_valid_oid(oid: str) -> bool:
    text = (oid or "").strip()
    if not text:
        return False
    parts = text.split(".")
    return len(parts) >= 2 and all(part.isdigit() for part in parts if part)


def resolve_host_ips(host: str, *, limit: int = 4) -> list[str]:
    normalized = _normalise_host(host)
    try:
        info = socket.getaddrinfo(normalized, None)
    except OSError as exc:
        raise ValueError("unknown host") from exc

    ips = []
    for entry in info:
        sockaddr = entry[4]
        if sockaddr:
            if isinstance(sockaddr[0], str):
                ips.append(sockaddr[0])
    if not ips:
        raise ValueError("host has no resolvable IP")
    deduped = []
    for item in ips:
        if item not in deduped:
            deduped.append(item)
        if len(deduped) >= limit:
            break
    return deduped
