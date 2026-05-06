"""Create or update Veklom operator schedules in Upstash QStash.

This is intentionally an operator-side script. It does not ship in buyer
packages and it does not store secrets. It reads the QStash token and scoped
worker keys from the environment, then upserts schedules with deterministic
IDs so reruns are safe.
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

import httpx


QSTASH_API = "https://qstash.upstash.io/v2"


@dataclass(frozen=True)
class ScheduleSpec:
    schedule_id: str
    destination_path: str
    cron: str
    worker_key_env: str
    body: dict[str, Any]
    timeout: str = "30s"
    retries: int = 5


SCHEDULES = [
    ScheduleSpec(
        schedule_id="veklom-job-processor-30m",
        destination_path="/api/v1/jobs/process",
        cron="*/30 * * * *",
        worker_key_env="JOB_PROCESSOR_API_KEY",
        body={"trigger": "qstash", "source": "qstash", "worker": "job_processor"},
    ),
    ScheduleSpec(
        schedule_id="veklom-marketplace-automation-6h",
        destination_path="/api/v1/marketplace/automation/run",
        cron="0 */6 * * *",
        worker_key_env="MARKETPLACE_AUTOMATION_API_KEY",
        body={"trigger": "qstash", "source": "qstash", "worker": "marketplace_automation"},
    ),
    ScheduleSpec(
        schedule_id="veklom-marketplace-automation-monday-5h",
        destination_path="/api/v1/marketplace/automation/run",
        cron="15 */5 * * 1",
        worker_key_env="MARKETPLACE_AUTOMATION_API_KEY",
        body={"trigger": "qstash", "source": "qstash", "worker": "marketplace_automation_monday"},
    ),
]


def _required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


def _backend_url() -> str:
    return os.getenv("BACKEND_URL", "https://api.veklom.com").strip().rstrip("/")


def _create_or_update_schedule(client: httpx.Client, token: str, spec: ScheduleSpec) -> dict[str, Any]:
    worker_key = _required_env(spec.worker_key_env)
    destination = f"{_backend_url()}{spec.destination_path}"
    url = f"{QSTASH_API}/schedules/{quote(destination, safe='')}"
    response = client.post(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Upstash-Cron": spec.cron,
            "Upstash-Schedule-Id": spec.schedule_id,
            "Upstash-Method": "POST",
            "Upstash-Timeout": spec.timeout,
            "Upstash-Retries": str(spec.retries),
            "Upstash-Retry-Delay": "max(1000, pow(2, retried) * 1000)",
            "Upstash-Forward-Authorization": f"Bearer {worker_key}",
            "Upstash-Forward-Content-Type": "application/json",
            "Upstash-Redact-Fields": "body,header[Authorization]",
        },
        json=spec.body,
    )
    response.raise_for_status()
    payload = response.json()
    return {
        "schedule_id": spec.schedule_id,
        "qstash_schedule_id": payload.get("scheduleId"),
        "destination": destination,
        "cron": spec.cron,
    }


def _list_schedules(client: httpx.Client, token: str) -> list[dict[str, Any]]:
    response = client.get(
        f"{QSTASH_API}/schedules",
        headers={"Authorization": f"Bearer {token}"},
    )
    response.raise_for_status()
    return response.json()


def main() -> int:
    token = _required_env("QSTASH_TOKEN")
    dry_run = os.getenv("DRY_RUN", "").lower() in {"1", "true", "yes"}
    if dry_run:
        print(json.dumps({
            "dry_run": True,
            "backend_url": _backend_url(),
            "schedules": [
                {
                    "schedule_id": spec.schedule_id,
                    "destination": f"{_backend_url()}{spec.destination_path}",
                    "cron": spec.cron,
                    "worker_key_env": spec.worker_key_env,
                }
                for spec in SCHEDULES
            ],
        }, indent=2))
        return 0

    with httpx.Client(timeout=20.0) as client:
        results = [_create_or_update_schedule(client, token, spec) for spec in SCHEDULES]
        existing = _list_schedules(client, token)

    managed_ids = {spec.schedule_id for spec in SCHEDULES}
    managed_existing = [
        {
            "scheduleId": row.get("scheduleId"),
            "cron": row.get("cron"),
            "destination": row.get("destination"),
            "isPaused": row.get("isPaused"),
        }
        for row in existing
        if row.get("scheduleId") in managed_ids
    ]
    print(json.dumps({"upserted": results, "managed_existing": managed_existing}, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"QStash schedule sync failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1)
