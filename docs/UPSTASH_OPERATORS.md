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

## QStash Schedules

The repo owns three deterministic QStash schedules:

| Schedule ID | Cron | Destination |
|---|---:|---|
| `veklom-job-processor-30m` | `*/30 * * * *` | `/api/v1/jobs/process` |
| `veklom-marketplace-automation-6h` | `0 */6 * * *` | `/api/v1/marketplace/automation/run` |
| `veklom-marketplace-automation-monday-5h` | `15 */5 * * 1` | `/api/v1/marketplace/automation/run` |

These mirror the existing GitHub cron workers. QStash adds delivery retries, delivery logs, and schedule state outside GitHub Actions.

## Required GitHub Secrets

Set these in GitHub Actions secrets:

```text
QSTASH_TOKEN
BACKEND_URL
JOB_PROCESSOR_API_KEY
MARKETPLACE_AUTOMATION_API_KEY
```

`BACKEND_URL` should be `https://api.veklom.com` for production.

The worker keys must stay scoped. Do not use the owner/admin key here.

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
