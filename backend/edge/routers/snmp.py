"""SNMP input adapter endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from core.auth import get_current_user
from edge.connectors.snmp_client import SNMPReadError, read_snmp
from edge.core.normalizer import normalize
from edge.core.pipeline import process_pipeline
from edge.services.legacy_targets import validate_snmp_input_for_gateway

router = APIRouter(prefix="/edge", tags=["Edge"])


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
    return await process_pipeline(data, user)
