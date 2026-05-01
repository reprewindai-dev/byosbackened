"""SNMP input adapter endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from core.auth import get_current_user
from edge.core.normalizer import normalize
from edge.core.pipeline import process_pipeline
from edge.services.legacy_targets import build_decision_response, validate_snmp_input_for_gateway

router = APIRouter(prefix="/edge", tags=["Edge"])


class SNMPReadError(RuntimeError):
    """Router-level SNMP read error."""


def _load_snmp_client():
    """Load the runtime SNMP connector if present, otherwise fallback to inline impl."""
    try:
        from edge.connectors.snmp_client import SNMPReadError, read_snmp

        return SNMPReadError, read_snmp
    except ModuleNotFoundError:
        from pysnmp.hlapi import (
            CommunityData,
            ContextData,
            ObjectIdentity,
            ObjectType,
            SnmpEngine,
            UdpTransportTarget,
            getCmd,
        )

        class _SnmpReadError(RuntimeError):
            """Fallback SNMP read error."""

        def _read_snmp(ip: str, oid: str, community: str = "public", port: int = 161) -> str:
            iterator = getCmd(
                SnmpEngine(),
                CommunityData(community),
                UdpTransportTarget((ip, port), timeout=3, retries=2),
                ContextData(),
                ObjectType(ObjectIdentity(oid)),
            )
            error_indication, error_status, _, var_binds = next(iterator)
            if error_indication:
                raise _SnmpReadError(str(error_indication))
            if error_status:
                raise _SnmpReadError(str(error_status))
            if not var_binds:
                raise _SnmpReadError("SNMP response payload is empty")
            return str(var_binds[0][1])

        return _SnmpReadError, _read_snmp


def read_snmp(ip: str, oid: str) -> str:
    """Read SNMP through the connector while keeping imports lazy."""
    err_cls, reader = _load_snmp_client()
    try:
        return reader(ip, oid)
    except Exception as exc:
        if isinstance(exc, err_cls):
            raise SNMPReadError(str(exc)) from exc
        raise


@router.get("/snmp")
@router.get("/protocol/snmp")
async def read_snmp_route(ip: str, oid: str, user=Depends(get_current_user)):
    """Read a SNMP OID and ingest into edge execution pipeline."""
    try:
        ip, _ = validate_snmp_input_for_gateway(ip, oid)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    try:
        value = read_snmp(ip, oid)
    except SNMPReadError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    data = normalize("snmp", ip, oid, value)
    pipeline_result = await process_pipeline(data, user)
    response = build_decision_response(
        scenario="network",
        live=True,
        fallback=False,
        protocol="snmp",
        source=ip,
        signal={oid: data["value"]},
        public_demo=False,
        customer_route_cost_credits=40,
        raw={"pipeline_result": pipeline_result, "input": data},
    )
    if isinstance(pipeline_result, dict):
        response.update(pipeline_result)
    return response
