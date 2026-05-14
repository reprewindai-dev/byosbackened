"""Modbus connector for edge protocol ingestion."""

from __future__ import annotations

import logging
logger = logging.getLogger(__name__)


class ModbusReadError(RuntimeError):
    """Raised when Modbus read operations fail."""


class ModbusClient:
    """Small, production-safe Modbus RTU client wrapper."""

    def __init__(self, port: str = "/dev/ttyUSB0", baudrate: int = 9600, timeout: int | float = 2) -> None:
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self._client_class = self._load_client()

    @staticmethod
    def _load_client():
        try:
            from pymodbus.client import ModbusSerialClient
        except ModuleNotFoundError as exc:  # pragma: no cover - dependency optional
            raise ModbusReadError("pymodbus is not installed") from exc

        return ModbusSerialClient

    def read(self, address: int, slave: int = 1) -> float:
        """Read a single holding register and return it as a float."""
        if address < 0:
            raise ModbusReadError("Address must be non-negative")
        if slave < 1:
            raise ModbusReadError("Slave ID must be >= 1")

        client = self._client_class(method="rtu", port=self.port, baudrate=self.baudrate, timeout=self.timeout)
        try:
            if not client.connect():
                raise ModbusReadError(f"Failed to connect to Modbus device on {self.port}")

            result = client.read_holding_registers(address=address, count=1, slave=slave)
            if result.isError():
                raise ModbusReadError(f"Modbus device read error on address {address}, slave {slave}")

            if not hasattr(result, "registers") or not result.registers:
                raise ModbusReadError("Modbus read returned empty register payload")

            return float(result.registers[0])
        finally:
            try:
                client.close()
            except Exception:  # pragma: no cover - defensive cleanup
                logger.debug("Modbus client close failed", exc_info=True)
