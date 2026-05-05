"""SNMP connector for edge protocol ingestion."""

from __future__ import annotations

import asyncio
import threading
from typing import Any



class SNMPReadError(RuntimeError):
    """Raised when SNMP read operations fail."""


def _run_async_safely(coro: Any) -> Any:
    """Run an async SNMP operation from sync route code."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    result: dict[str, Any] = {}

    def _runner() -> None:
        try:
            result["value"] = asyncio.run(coro)
        except BaseException as exc:  # pragma: no cover - defensive bridge
            result["error"] = exc

    thread = threading.Thread(target=_runner, daemon=True)
    thread.start()
    thread.join()
    if "error" in result:
        raise result["error"]
    return result.get("value")


async def _read_snmp_v7(ip: str, oid: str, community: str, port: int) -> str:
    """Read one SNMP OID using the PySNMP 7 asyncio API."""
    try:
        from pysnmp.hlapi.v3arch.asyncio import ContextData
        from pysnmp.hlapi.v3arch.asyncio import CommunityData, ObjectIdentity, ObjectType, SnmpEngine
        from pysnmp.hlapi.v3arch.asyncio import UdpTransportTarget, get_cmd
    except ModuleNotFoundError as exc:  # pragma: no cover - dependency optional
        raise SNMPReadError("pysnmp is not installed") from exc
    except ImportError as exc:
        raise SNMPReadError("installed pysnmp does not expose the v7 asyncio API") from exc

    error_indication, error_status, _, var_binds = await get_cmd(
        SnmpEngine(),
        CommunityData(community),
        await UdpTransportTarget.create((ip, port), timeout=3, retries=2),
        ContextData(),
        ObjectType(ObjectIdentity(oid)),
    )
    if error_indication:
        raise SNMPReadError(str(error_indication))
    if error_status:
        raise SNMPReadError(str(error_status))
    if not var_binds:
        raise SNMPReadError("SNMP response payload is empty")
    return str(var_binds[0][1])


def _read_snmp_legacy(ip: str, oid: str, community: str, port: int) -> str:
    """Read one SNMP OID using the legacy PySNMP 4 sync API."""
    try:
        from pysnmp.hlapi import ContextData
        from pysnmp.hlapi import CommunityData, ObjectIdentity, ObjectType, SnmpEngine
        from pysnmp.hlapi import UdpTransportTarget, getCmd
    except ModuleNotFoundError as exc:  # pragma: no cover - dependency optional
        raise SNMPReadError("pysnmp is not installed") from exc
    except ImportError as exc:
        raise SNMPReadError("installed pysnmp does not expose a supported SNMP API") from exc

    iterator = getCmd(
        SnmpEngine(),
        CommunityData(community),
        UdpTransportTarget((ip, port), timeout=3, retries=2),
        ContextData(),
        ObjectType(ObjectIdentity(oid)),
    )
    error_indication, error_status, _, var_binds = next(iterator)
    if error_indication:
        raise SNMPReadError(str(error_indication))
    if error_status:
        raise SNMPReadError(str(error_status))
    if not var_binds:
        raise SNMPReadError("SNMP response payload is empty")
    return str(var_binds[0][1])


def read_snmp(ip: str, oid: str, community: str = "public", port: int = 161) -> str:
    """Read one SNMP OID from the given host."""
    if not ip:
        raise SNMPReadError("IP address is required")
    if not oid:
        raise SNMPReadError("OID is required")

    try:
        return _run_async_safely(_read_snmp_v7(ip, oid, community, port))
    except SNMPReadError as exc:
        if "v7 asyncio API" not in str(exc):
            raise
    return _read_snmp_legacy(ip, oid, community, port)
