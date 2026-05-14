"""Modbus input adapter endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from core.auth import get_current_user
from edge.core.normalizer import normalize
from edge.core.pipeline import process_pipeline
from edge.services.legacy_targets import build_decision_response, resolve_customer_modbus_target

router = APIRouter(prefix="/edge", tags=["Edge"])

_CLIENTS: dict[tuple[str, int, int | float], object] = {}


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


def _get_client(port: str = "/dev/ttyUSB0", baudrate: int = 9600, timeout: int | float = 2):
    """Return a cached Modbus client instance."""
    cache_key = (port, baudrate, timeout)
    if cache_key not in _CLIENTS:
        _, client_cls = _load_modbus_client()
        _CLIENTS[cache_key] = client_cls(port=port, baudrate=baudrate, timeout=timeout)
    return _CLIENTS[cache_key]


@router.get("/modbus")
@router.get("/protocol/modbus")
async def read_modbus(
    request: Request = None,
    target: str = Query(default="local-rtu-demo"),
    register_key: str = Query(default="temperature_c"),
    user=Depends(get_current_user),
):
    """Read an allowlisted Modbus register and ingest into edge execution pipeline."""
    if request is not None:
        allowed_query_params = {"target", "register_key"}
        unexpected_params = set(request.query_params.keys()) - allowed_query_params
        if unexpected_params:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported query parameter(s): {', '.join(sorted(unexpected_params))}",
            )

    try:
        resolved = resolve_customer_modbus_target(target, register_key)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    try:
        err_cls, _ = _load_modbus_client()
        value = _get_client(
            port=resolved.port,
            baudrate=resolved.baudrate,
            timeout=resolved.timeout,
        ).read(address=resolved.address, slave=resolved.slave)
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

    data = normalize("modbus", resolved.source, resolved.metric, value)
    pipeline_result = await process_pipeline(data, user)
    response = build_decision_response(
        scenario="machine",
        live=True,
        fallback=False,
        protocol="modbus",
        source=resolved.source,
        signal={resolved.metric: data["value"]},
        public_demo=False,
        customer_route_cost_credits=40,
        raw={
            "pipeline_result": pipeline_result,
            "input": data,
            "target": resolved.target_key,
            "register_key": resolved.register_key,
            "address": resolved.address,
            "slave": resolved.slave,
        },
    )
    if isinstance(pipeline_result, dict):
        response.update(pipeline_result)
    return response
