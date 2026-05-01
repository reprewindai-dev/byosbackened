"""SNMP input adapter endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from core.auth import get_current_user
from edge.core.normalizer import normalize
from edge.core.pipeline import process_pipeline
from edge.services.legacy_targets import build_decision_response, resolve_customer_snmp_target

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


def read_snmp(ip: str, oid: str, *, community: str = "public", port: int = 161) -> str:
    """Read SNMP through the connector while keeping imports lazy."""
    err_cls, reader = _load_snmp_client()
    try:
        return reader(ip, oid, community=community, port=port)
    except Exception as exc:
        if isinstance(exc, err_cls):
            raise SNMPReadError(str(exc)) from exc
        raise


@router.get("/snmp")
@router.get("/protocol/snmp")
async def read_snmp_route(
    request: Request = None,
    target: str = Query(default="pysnmp-public"),
    oid_key: str = Query(default="sys_descr"),
    user=Depends(get_current_user),
):
    """Read an allowlisted SNMP OID and ingest into edge execution pipeline."""
    if request is not None:
        allowed_query_params = {"target", "oid_key"}
        unexpected_params = set(request.query_params.keys()) - allowed_query_params
        if unexpected_params:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported query parameter(s): {', '.join(sorted(unexpected_params))}",
            )

    try:
        resolved = resolve_customer_snmp_target(target, oid_key)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    try:
        value = read_snmp(
            resolved.host,
            resolved.oid,
            community=resolved.community,
            port=resolved.port,
        )
    except SNMPReadError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    data = normalize("snmp", resolved.source, resolved.metric, value)
    pipeline_result = await process_pipeline(data, user)
    response = build_decision_response(
        scenario="network",
        live=True,
        fallback=False,
        protocol="snmp",
        source=resolved.source,
        signal={resolved.metric: data["value"]},
        public_demo=False,
        customer_route_cost_credits=40,
        raw={
            "pipeline_result": pipeline_result,
            "input": data,
            "target": resolved.target_key,
            "oid_key": resolved.oid_key,
        },
    )
    if isinstance(pipeline_result, dict):
        response.update(pipeline_result)
    return response
