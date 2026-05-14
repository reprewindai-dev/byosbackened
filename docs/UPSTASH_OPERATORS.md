# Upstash Operator Runtime

This file defines how Veklom uses Upstash without moving the production backend out of Hetzner/Coolify.

## Decision

Production API stays on Hetzner/Coolify.

Upstash is operator infrastructure:

- Redis: optional managed state/cache for edge or serverless workers.
- QStash: reliable scheduled HTTP delivery and retries for internal worker endpoints.
- Workflow: later, for multi-step agent jobs that need durable checkpoints.
- Vector: later, for competitor, vendor, policy, and support memory.
- Box: later, for private internal agent workstations. Box is not part of the buyer backend package.
- Builder Agents: optional Box experiment for clean-room marketplace tool research and build intake. These agents are Veklom-internal only and must write operator audit events before any marketplace action.

## QStash Schedules

The repo owns three deterministic QStash schedules:

| Schedule ID | Cron | Destination |
|---|---:|---|
| `veklom-job-processor-30m` | `*/30 * * * *` | `/api/v1/jobs/process` |
| `veklom-marketplace-automation-6h` | `0 */6 * * *` | `/api/v1/marketplace/automation/run` |
| `veklom-marketplace-automation-monday-5h` | `15 */5 * * 1` | `/api/v1/marketplace/automation/run` |

These mirror the existing GitHub cron workers. QStash adds delivery retries, delivery logs, and schedule state outside GitHub Actions.

Optional experiment schedule:

| Schedule ID | Cron | Destination | Enablement |
|---|---:|---|---|
| `veklom-builder-agent-box-heartbeat-6h` | `22 */6 * * *` | `/api/v1/internal/operators/workers/builder-scout/heartbeat` | `ENABLE_BUILDER_AGENT_QSTASH=true` |

The Builder Agent schedule is intentionally disabled by default. It is a Box experiment readiness heartbeat, not a scraper runner. Real research jobs must be launched from the Box worker after UACP approval and must record runs through `/api/v1/internal/operators/runs`.

## Required GitHub Secrets

Set these in GitHub Actions secrets:

```text
QSTASH_TOKEN
BACKEND_URL
JOB_PROCESSOR_API_KEY
MARKETPLACE_AUTOMATION_API_KEY
INTERNAL_OPERATOR_TOKEN
```

`BACKEND_URL` should be `https://api.veklom.com` for production.

The worker keys must stay scoped. Do not use the owner/admin key here.

`INTERNAL_OPERATOR_TOKEN` must be a superuser-owned automation key. It is only required when `ENABLE_BUILDER_AGENT_QSTASH=true`.

## Sync Command

Manual GitHub workflow:

```text
QStash Schedule Sync
```

Or local dry run:

```bash
DRY_RUN=true QSTASH_TOKEN=dummy python backend/scripts/setup_qstash_schedules.py
```

Production sync:

```bash
QSTASH_TOKEN=... \
BACKEND_URL=https://api.veklom.com \
JOB_PROCESSOR_API_KEY=... \
MARKETPLACE_AUTOMATION_API_KEY=... \
python backend/scripts/setup_qstash_schedules.py
```

## Guardrails

- QStash receives only scoped internal worker keys.
- Forwarded authorization headers are redacted from QStash logs.
- Schedule IDs are deterministic, so rerunning the sync updates schedules instead of creating duplicates.
- GitHub cron stays as fallback until QStash has run cleanly for at least 7 days.
- Box is not allowed to hold production owner keys.
- Builder Agents may ingest public problem signals, but may not clone, copy, or repackage third-party code.
- Builder Agent output must include source lineage, license status, clean-room notes, tests, and release-gate evidence before marketplace publication.
