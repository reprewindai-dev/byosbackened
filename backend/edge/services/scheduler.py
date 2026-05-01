"""Polling scheduler primitives for legacy protocol polling workflows."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from edge.connectors.modbus_client import ModbusReadError, ModbusClient
from edge.connectors.snmp_client import SNMPReadError, read_snmp
from edge.core.normalizer import normalize
from edge.core.pipeline import process_pipeline

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ModbusPollTarget:
    address: int
    source: str = "modbus-device"
    slave: int = 1


@dataclass(frozen=True)
class SnmpPollTarget:
    ip: str
    oid: str
    source: str = "snmp-device"
    community: str = "public"


async def poll_devices(
    user,
    modbus_targets: list[ModbusPollTarget] | None = None,
    snmp_targets: list[SnmpPollTarget] | None = None,
    interval_seconds: float = 5.0,
    iterations: int | None = None,
    stop_event: asyncio.Event | None = None,
    on_result: Callable[[dict], Awaitable[None]] | None = None,
    modbus_port: str = "/dev/ttyUSB0",
) -> int:
    """
    Poll configured targets and feed normalized reads into the edge pipeline.

    Returns the number of successfully ingested samples.
    """
    modbus_targets = modbus_targets or []
    snmp_targets = snmp_targets or []
    modbus_client = ModbusClient(port=modbus_port)
    executed = 0

    if on_result is None:
        on_result = lambda event: process_pipeline(event, user)  # type: ignore[return-value]

    if not modbus_targets and not snmp_targets:
        logger.info("No polling targets provided; exiting scheduler")
        return 0

    async def _handle_modbus(target: ModbusPollTarget) -> int:
        try:
            value = await asyncio.to_thread(modbus_client.read, target.address, target.slave)
            payload = normalize("modbus", target.source, str(target.address), value)
            result = on_result(payload)
            if asyncio.iscoroutine(result):
                await result
            return 1
        except ModbusReadError:
            logger.debug("Modbus polling failed for address=%s", target.address, exc_info=True)
            return 0
        except Exception:
            logger.debug("Unexpected Modbus polling error for address=%s", target.address, exc_info=True)
            return 0

    async def _handle_snmp(target: SnmpPollTarget) -> int:
        try:
            value = await asyncio.to_thread(read_snmp, target.ip, target.oid, target.community)
            payload = normalize("snmp", target.source, target.oid, value)
            result = on_result(payload)
            if asyncio.iscoroutine(result):
                await result
            return 1
        except SNMPReadError:
            logger.debug("SNMP polling failed for target=%s oid=%s", target.ip, target.oid, exc_info=True)
            return 0
        except Exception:
            logger.debug("Unexpected SNMP polling error for target=%s oid=%s", target.ip, target.oid, exc_info=True)
            return 0

    loop_count = 0
    while True:
        if iterations is not None and loop_count >= iterations:
            break
        if stop_event is not None and stop_event.is_set():
            break

        loop_count += 1
        for target in modbus_targets:
            executed += await _handle_modbus(target)
        for target in snmp_targets:
            executed += await _handle_snmp(target)

        if iterations is not None and loop_count >= iterations:
            break
        if interval_seconds > 0:
            await asyncio.sleep(interval_seconds)

    return executed
