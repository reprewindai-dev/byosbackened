"""Modbus TCP connector for live protocol canaries."""
from __future__ import annotations

import inspect
import logging

logger = logging.getLogger(__name__)


class ModbusTCPReadError(RuntimeError):
    """Raised when Modbus TCP read operations fail."""


class ModbusTCPClient:
    """Small wrapper around pymodbus' TCP client for a single holding-register read."""

    def __init__(self, host: str, port: int = 502, timeout: int | float = 4) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout
        self._client_class = self._load_client()

    @staticmethod
    def _load_client():
        try:
            from pymodbus.client import ModbusTcpClient
        except ModuleNotFoundError as exc:  # pragma: no cover - dependency optional
            raise ModbusTCPReadError("pymodbus is not installed") from exc

        return ModbusTcpClient

    def read_holding_register(self, address: int, slave: int = 1, count: int = 1) -> float:
        """Read a single holding register and return it as a float."""
        if address < 0:
            raise ModbusTCPReadError("Address must be non-negative")
        if slave < 1:
            raise ModbusTCPReadError("Slave ID must be >= 1")
        if count < 1:
            raise ModbusTCPReadError("Count must be >= 1")

        client = self._client_class(host=self.host, port=self.port, timeout=self.timeout)
        try:
            if not client.connect():
                raise ModbusTCPReadError(f"Failed to connect to Modbus TCP device on {self.host}:{self.port}")

            read_kwargs = {"address": address, "count": count}
            parameters = inspect.signature(client.read_holding_registers).parameters
            if "slave" in parameters:
                read_kwargs["slave"] = slave
            elif "unit" in parameters:
                read_kwargs["unit"] = slave
            else:  # pragma: no cover - defensive compatibility fallback
                read_kwargs["slave"] = slave

            result = client.read_holding_registers(**read_kwargs)
            if result.isError():
                raise ModbusTCPReadError(f"Modbus TCP read error on address {address}, slave {slave}")
            if not hasattr(result, "registers") or not result.registers:
                raise ModbusTCPReadError("Modbus TCP read returned empty register payload")
            return float(result.registers[0])
        finally:
            try:
                client.close()
            except Exception:  # pragma: no cover - defensive cleanup
                logger.debug("Modbus TCP client close failed", exc_info=True)
