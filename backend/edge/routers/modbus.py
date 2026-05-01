"""Modbus input adapter endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from core.auth import get_current_user
from edge.core.normalizer import normalize
from edge.core.pipeline import process_pipeline
from edge.services.legacy_targets import build_decision_response

router = APIRouter(prefix="/edge", tags=["Edge"])

_CLIENT: object | None = None


def _load_modbus_client():
    """Load the Modbus connector if present, otherwise fallback to inline impl."""
    try:
        from edge.connectors.modbus_client import ModbusClient, ModbusReadError

        return ModbusReadError, ModbusClient
    except ModuleNotFoundError:
        from pymodbus.client import ModbusSerialClient

        class _ModbusReadError(RuntimeError):
            """Fallback Modbus read error."""

        class _ModbusClient:
            def __init__(self, port: str = "/dev/ttyUSB0", baudrate: int = 9600, timeout: int | float = 2) -> None:
                self.port = port
                self.baudrate = baudrate
                self.timeout = timeout
                self._client = ModbusSerialClient(
                    method="rtu",
                    port=self.port,
                    baudrate=self.baudrate,
                    timeout=self.timeout,
                )

            def read(self, address: int, slave: int = 1) -> float:
                if address < 0:
                    raise _ModbusReadError("Address must be non-negative")
                if slave < 1:
                    raise _ModbusReadError("Slave ID must be >= 1")

                if not self._client.connect():
                    raise _ModbusReadError(f"Failed to connect to Modbus device on {self.port}")

                try:
                    result = self._client.read_holding_registers(address=address, count=1, slave=slave)
                    if getattr(result, "isError", lambda: False)():
                        raise _ModbusReadError(f"Modbus device read error on address {address}, slave {slave}")
                    if not hasattr(result, "registers") or not result.registers:
                        raise _ModbusReadError("Modbus read returned empty register payload")
                    return float(result.registers[0])
                finally:
                    try:
                        self._client.close()
                    except Exception:
                        pass

        return _ModbusReadError, _ModbusClient


def _get_client():
    """Return a cached Modbus client instance."""
    global _CLIENT
    if _CLIENT is None:
        _, client_cls = _load_modbus_client()
        _CLIENT = client_cls()
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
        err_cls, _ = _load_modbus_client()
        value = _get_client().read(address=address, slave=slave)
    except Exception as exc:
        if isinstance(exc, err_cls):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=str(exc),
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    data = normalize("modbus", "device", str(address), value)
    pipeline_result = await process_pipeline(data, user)
    response = build_decision_response(
        scenario="machine",
        live=True,
        fallback=False,
        protocol="modbus",
        source="device",
        signal={str(address): data["value"]},
        public_demo=False,
        customer_route_cost_credits=40,
        raw={"pipeline_result": pipeline_result, "input": data, "slave": slave},
    )
    if isinstance(pipeline_result, dict):
        response.update(pipeline_result)
    return response
