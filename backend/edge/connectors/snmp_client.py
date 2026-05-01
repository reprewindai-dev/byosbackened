"""SNMP connector for edge protocol ingestion."""

from __future__ import annotations



class SNMPReadError(RuntimeError):
    """Raised when SNMP read operations fail."""


def read_snmp(ip: str, oid: str, community: str = "public", port: int = 161) -> str:
    """Read one SNMP OID from the given host."""
    if not ip:
        raise SNMPReadError("IP address is required")
    if not oid:
        raise SNMPReadError("OID is required")

    try:
        from pysnmp.hlapi import ContextData
        from pysnmp.hlapi import CommunityData, ObjectIdentity, ObjectType, SnmpEngine
        from pysnmp.hlapi import getCmd, UdpTransportTarget
    except ModuleNotFoundError as exc:  # pragma: no cover - dependency optional
        raise SNMPReadError("pysnmp is not installed") from exc

    iterator = getCmd(
        SnmpEngine(),
        CommunityData(community),
        UdpTransportTarget((ip, port), timeout=3, retries=2),
        ContextData(),
        ObjectType(ObjectIdentity(oid)),
    )

    errorIndication, errorStatus, _, varBinds = next(iterator)
    if errorIndication:
        raise SNMPReadError(str(errorIndication))
    if errorStatus:
        raise SNMPReadError(str(errorStatus))
    if not varBinds:
        raise SNMPReadError("SNMP response payload is empty")

    return str(varBinds[0][1])
