"""Machine fingerprint generation for license activation."""
from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import socket
import subprocess
import uuid
from typing import Dict, List, Optional


def _normalize(value: Optional[str]) -> str:
    if not value:
        return ""
    cleaned = str(value).strip().lower()
    cleaned = re.sub(r"[^a-z0-9._:-]+", "", cleaned)
    return cleaned


def _run_command(command: List[str], timeout: int = 2) -> str:
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        output = (result.stdout or "").strip()
        if result.returncode == 0 and output:
            return output
    except Exception:
        return ""
    return ""


def _windows_cpu_id() -> str:
    output = _run_command(["wmic", "cpu", "get", "ProcessorId", "/value"])
    match = re.search(r"ProcessorId=(.+)", output, re.IGNORECASE)
    return match.group(1).strip() if match else ""


def _windows_disk_serial() -> str:
    output = _run_command(["wmic", "diskdrive", "get", "SerialNumber", "/value"])
    match = re.search(r"SerialNumber=(.+)", output, re.IGNORECASE)
    return match.group(1).strip() if match else ""


def _windows_machine_uuid() -> str:
    output = _run_command(["wmic", "csproduct", "get", "UUID", "/value"])
    match = re.search(r"UUID=(.+)", output, re.IGNORECASE)
    return match.group(1).strip() if match else ""


def _linux_machine_uuid() -> str:
    paths = [
        "/sys/class/dmi/id/product_uuid",
        "/var/lib/dbus/machine-id",
        "/etc/machine-id",
    ]
    for path in paths:
        try:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as handle:
                    value = handle.read().strip()
                    if value:
                        return value
        except Exception:
            continue
    return ""


def _linux_disk_serial() -> str:
    output = _run_command(["lsblk", "-dn", "-o", "SERIAL"])
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    return lines[0] if lines else ""


def _cpu_identifier() -> str:
    system = platform.system().lower()
    if system == "windows":
        return _windows_cpu_id()
    if system == "linux":
        try:
            with open("/proc/cpuinfo", "r", encoding="utf-8") as handle:
                for line in handle:
                    if "serial" in line.lower() or "model name" in line.lower():
                        value = line.split(":", 1)[-1].strip()
                        if value:
                            return value
        except Exception:
            pass
    return platform.processor() or platform.machine()


def _mac_addresses() -> List[str]:
    values: List[str] = []
    system = platform.system().lower()
    try:
        node = uuid.getnode()
        values.append(f"{node:012x}")
    except Exception:
        pass
    if system == "windows":
        output = _run_command(["getmac", "/fo", "csv", "/nh"])
        for line in output.splitlines():
            parts = [part.strip('"') for part in line.split(",")]
            if parts:
                values.append(parts[0])
    elif system == "linux":
        try:
            for iface in os.listdir("/sys/class/net"):
                path = f"/sys/class/net/{iface}/address"
                if os.path.exists(path):
                    with open(path, "r", encoding="utf-8") as handle:
                        mac = handle.read().strip()
                        if mac and mac != "00:00:00:00:00:00":
                            values.append(mac)
        except Exception:
            pass
    try:
        values.append(socket.gethostname())
    except Exception:
        pass
    return values


def collect_machine_fingerprint_inputs() -> Dict[str, str]:
    """Collect stable machine identity inputs with best-effort fallbacks."""
    system = platform.system().lower()
    hostname = socket.gethostname() or platform.node()
    values = {
        "hostname": _normalize(hostname),
        "cpu": _normalize(_cpu_identifier()),
        "machine_uuid": "",
        "disk_serial": "",
        "mac": "",
        "platform": _normalize(platform.platform()),
    }

    if system == "windows":
        values["machine_uuid"] = _normalize(_windows_machine_uuid())
        values["disk_serial"] = _normalize(_windows_disk_serial())
    elif system == "linux":
        values["machine_uuid"] = _normalize(_linux_machine_uuid())
        values["disk_serial"] = _normalize(_linux_disk_serial())

    macs = [_normalize(item) for item in _mac_addresses()]
    values["mac"] = ",".join([item for item in macs if item])
    return values


def get_machine_fingerprint() -> str:
    """Return a deterministic fingerprint for this machine."""
    inputs = collect_machine_fingerprint_inputs()
    payload = json.dumps(inputs, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return f"vklm_{digest}"
