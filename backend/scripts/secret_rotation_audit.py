"""Audit secret rotation age and worker ownership without exposing values."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Finding:
    severity: str
    owner: str
    name: str
    message: str
    action: str


def _parse_time(value: str) -> datetime | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _github_secrets_from_cli(repo: str | None) -> dict[str, datetime]:
    cmd = ["gh", "secret", "list", "--json", "name,updatedAt"]
    if repo:
        cmd.extend(["--repo", repo])
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    rows = json.loads(result.stdout or "[]")
    secrets: dict[str, datetime] = {}
    for row in rows:
        updated_at = _parse_time(row.get("updatedAt", ""))
        if updated_at:
            secrets[row["name"]] = updated_at
    return secrets


def _github_secrets_from_file(path: Path) -> dict[str, datetime]:
    rows = _load_json(path)
    if isinstance(rows, dict) and "value" in rows:
        rows = rows["value"]
    secrets: dict[str, datetime] = {}
    for row in rows:
        updated_at = _parse_time(row.get("updatedAt", ""))
        if updated_at:
            secrets[row["name"]] = updated_at
    return secrets


def _query_stale_database_keys(database_url: str, max_age_days: int) -> list[dict[str, Any]]:
    import psycopg2  # type: ignore[import-not-found]

    query = """
        SELECT workspace_id, key_preview, created_at,
               EXTRACT(DAY FROM NOW() - created_at) AS age_days
        FROM api_keys
        WHERE is_active = true
          AND created_at < NOW() - (%s || ' days')::interval
        ORDER BY age_days DESC
    """
    conn = psycopg2.connect(database_url)
    try:
        with conn.cursor() as cur:
            cur.execute(query, (max_age_days,))
            rows = cur.fetchall()
    finally:
        conn.close()
    return [
        {
            "workspace_id": str(row[0]),
            "key_preview": row[1],
            "created_at": row[2].isoformat() if row[2] else "",
            "age_days": int(row[3]),
        }
        for row in rows
    ]


def _render_report(findings: list[Finding]) -> str:
    if not findings:
        return "## Secret Rotation Guardian\n\nAll configured secrets are present and inside rotation windows.\n"

    lines = [
        "## Secret Rotation Guardian",
        "",
        "The rotation guardian found secrets or internal keys that need operator action. No secret values were read or printed.",
        "",
        "| Severity | Worker | Secret / Key | Finding | Required action |",
        "| --- | --- | --- | --- | --- |",
    ]
    for item in findings:
        lines.append(
            f"| {item.severity} | {item.owner} | `{item.name}` | {item.message} | {item.action} |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--policy",
        default=os.getenv("SECRET_ROTATION_POLICY_PATH", "ops/secret-rotation-policy.json"),
    )
    parser.add_argument("--github-secrets-json", default="")
    parser.add_argument("--repo", default=os.getenv("GITHUB_REPOSITORY", ""))
    parser.add_argument("--report", default=os.getenv("SECRET_ROTATION_REPORT", "secret-rotation-report.md"))
    parser.add_argument(
        "--force-rotate",
        default=os.getenv("FORCE_ROTATE_SECRETS", ""),
        help="Comma-separated secret names to flag for immediate rotation.",
    )
    parser.add_argument("--skip-db", action="store_true")
    args = parser.parse_args()

    policy_path = Path(args.policy)
    policy = _load_json(policy_path)
    now = datetime.now(UTC)
    forced = {name.strip() for name in args.force_rotate.split(",") if name.strip()}

    findings: list[Finding] = []
    github_metadata_available = True
    try:
        if args.github_secrets_json:
            github_secrets = _github_secrets_from_file(Path(args.github_secrets_json))
        else:
            github_secrets = _github_secrets_from_cli(args.repo or None)
    except Exception as exc:  # noqa: BLE001 - report operational failure without leaking env
        github_metadata_available = False
        findings.append(
            Finding(
                severity="critical",
                owner="BOUNCER",
                name="SECRET_ROTATION_GH_TOKEN",
                message=f"Unable to inspect GitHub secret metadata: {exc.__class__.__name__}.",
                action="Add a fine-scoped GitHub token as SECRET_ROTATION_GH_TOKEN with repository Actions secrets read permission, then rerun the guardian.",
            )
        )
        github_secrets = {}

    for secret in policy.get("provider_secrets", []):
        if not github_metadata_available:
            continue
        name = secret["name"]
        owner = secret.get("owner", "BOUNCER")
        max_age_days = int(secret.get("max_age_days") or policy.get("max_default_age_days", 90))
        critical = bool(secret.get("critical", False))
        action = secret.get("rotation_action", "Rotate this secret and update all secret stores.")
        updated_at = github_secrets.get(name)

        if updated_at is None:
            severity = "critical" if critical else "warning"
            findings.append(
                Finding(
                    severity=severity,
                    owner=owner,
                    name=name,
                    message="Secret metadata was not found in GitHub Actions.",
                    action=action,
                )
            )
            continue

        age_days = (now - updated_at).days
        if name in forced:
            findings.append(
                Finding(
                    severity="critical",
                    owner=owner,
                    name=name,
                    message=f"Forced rotation requested. Current metadata age is {age_days} day(s).",
                    action=action,
                )
            )
        elif age_days > max_age_days:
            severity = "critical" if critical else "warning"
            findings.append(
                Finding(
                    severity=severity,
                    owner=owner,
                    name=name,
                    message=f"Secret metadata age is {age_days} days; policy limit is {max_age_days} days.",
                    action=action,
                )
            )

    db_policy = policy.get("database_api_keys", {})
    if not args.skip_db and db_policy:
        database_url = os.getenv("DATABASE_URL", "")
        if not database_url:
            findings.append(
                Finding(
                    severity="critical",
                    owner=db_policy.get("owner", "BOUNCER"),
                    name="DATABASE_URL",
                    message="DATABASE_URL is required to audit internal API key rotation.",
                    action="Set DATABASE_URL for the rotation guardian or run with --skip-db for local checks.",
                )
            )
        else:
            try:
                max_age_days = int(db_policy.get("max_age_days", 90))
                stale_keys = _query_stale_database_keys(database_url, max_age_days)
                for stale in stale_keys:
                    findings.append(
                        Finding(
                            severity="critical" if db_policy.get("critical", True) else "warning",
                            owner=db_policy.get("owner", "BOUNCER"),
                            name=f"api_keys:{stale['workspace_id']}:{stale['key_preview']}",
                            message=f"Internal API key age is {stale['age_days']} days; policy limit is {max_age_days} days.",
                            action=db_policy.get("rotation_action", "Rotate stale internal API keys."),
                        )
                    )
            except Exception as exc:  # noqa: BLE001 - operational failure, no secret values
                findings.append(
                    Finding(
                        severity="critical",
                        owner=db_policy.get("owner", "BOUNCER"),
                        name="DATABASE_API_KEYS",
                        message=f"Unable to audit database API keys: {exc.__class__.__name__}",
                        action="Verify database connectivity and rerun the rotation guardian.",
                    )
                )

    report = _render_report(findings)
    Path(args.report).write_text(report, encoding="utf-8")
    print(report)
    return 1 if any(item.severity == "critical" for item in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
