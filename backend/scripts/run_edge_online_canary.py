"""Run the live edge protocol canary and print a compact proof table."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


CURRENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = CURRENT_DIR.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.append(str(REPO_ROOT))

from edge.services.protocol_canary import run_protocol_canary


def _bool_to_text(value: bool) -> str:
    return "PASS" if value else "FAIL"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the live Veklom legacy protocol canary.")
    parser.add_argument(
        "--live",
        action="store_true",
        default=os.environ.get("VEKLOM_RUN_LIVE_PROTOCOL_CANARIES") == "1",
        help="Run the actual allowlisted public network checks.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.live:
        print("Live protocol canaries are disabled.")
        print("Set VEKLOM_RUN_LIVE_PROTOCOL_CANARIES=1 or pass --live to run the public checks.")
        return 1

    report = run_protocol_canary()
    checks = report["checks"]
    print(f"Status: {report['status']}")
    print(f"Generated at: {report['generated_at']}")
    print("")
    for label, key in [
        ("SNMP", "snmp"),
        ("Modbus TCP", "modbus_tcp"),
        ("MQTT", "mqtt"),
        ("Webhook", "webhook"),
    ]:
        check = checks[key]
        print(
            f"{label}: {_bool_to_text(check['status'] == 'passed')}"
            f" (connect={_bool_to_text(check.get('connect_ok', False))}"
            f", normalize={_bool_to_text(check.get('normalized_ok', False))}"
            f", decision={_bool_to_text(check.get('decision_ok', False))}"
            f", audit={_bool_to_text(check.get('audit_ok', False))})"
        )
        if check.get("error"):
            print(f"  Error: {check['error']}")
    return 0 if report["status"] == "ok" else 2


if __name__ == "__main__":
    raise SystemExit(main())
