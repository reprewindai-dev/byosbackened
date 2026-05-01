"""Commercial machine fingerprinting for buyer license binding."""
from __future__ import annotations

import hashlib
import json
import os
import platform
import socket
import uuid
from pathlib import Path
from typing import Any


def _read_first(paths: list[str]) -> str:
    for item in paths:
        try:
            path = Path(item)
            if path.exists():
                value = path.read_text(encoding="utf-8", errors="ignore").strip()
                if value:
                    return value
        except Exception:
            continue
    return ""


def _install_uuid() -> str:
    configured = os.getenv("VEKLOM_INSTALL_UUID", "").strip()
    if configured:
        return configured
    path = Path(os.getenv("VEKLOM_INSTALL_UUID_PATH", "~/.veklom/install.uuid")).expanduser()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            existing = path.read_text(encoding="utf-8").strip()
            if existing:
                return existing
        generated = str(uuid.uuid4())
        path.write_text(generated, encoding="utf-8")
        return generated
    except Exception:
        return ""


def collect_machine_signals() -> dict[str, Any]:
    """Collect stable, non-secret signals. No customer data is included."""
    machine_id = _read_first([
        "/etc/machine-id",
        "/var/lib/dbus/machine-id",
        "/sys/class/dmi/id/product_uuid",
    ])
    container_marker = _read_first([
        "/proc/self/cgroup",
        "/etc/hostname",
    ])
    return {
        "platform": platform.platform(),
        "system": platform.system(),
        "machine": platform.machine(),
        "hostname": socket.gethostname(),
        "machine_id": machine_id,
        "install_uuid": _install_uuid(),
        "container_marker": hashlib.sha256(container_marker.encode("utf-8")).hexdigest() if container_marker else "",
    }


def get_machine_fingerprint() -> str:
    material = json.dumps(collect_machine_signals(), sort_keys=True, separators=(",", ":"))
    return "vklm_" + hashlib.sha256(material.encode("utf-8")).hexdigest()
