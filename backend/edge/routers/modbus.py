"""Modbus input adapter endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from core.auth import get_current_user
from edge.connectors.modbus_client import ModbusClient, ModbusReadError
from edge.core.normalizer import normalize
from edge.core.pipeline import process_pipeline

router = APIRouter(prefix="/edge", tags=["Edge"])


_CLIENT: ModbusClient | None = None


def _get_client() -> ModbusClient:
    """Return a cached Modbus client instance."""
    global _CLIENT
    if _CLIENT is None:
        _CLIENT = ModbusClient()
    return _CLIENT


@router.get("/modbus")
@router.get("/protocol/modbus")
async def read_modbus(address: int, slave: int = 1, user=Depends(get_current_user)):
    """Read a Modbus RTU holding register and ingest into edge execution pipeline."""
    if address < 0 or address > 65535:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="address must be an integer between 0 and 65535",
        )
    if slave < 1 or slave > 247:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="slave must be between 1 and 247",
        )

    try:
        value = _get_client().read(address=address, slave=slave)
    except ModbusReadError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    data = normalize("modbus", "device", str(address), value)
    return await process_pipeline(data, user)
