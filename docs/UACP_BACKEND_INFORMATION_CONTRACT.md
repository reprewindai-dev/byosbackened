# UACP Backend Information Contract

## Objective

Define the production contract between the Veklom backend and UACP V3 so the Command Center displays real product state plus UACP institutional interpretation. The backend owns what happened. UACP owns what the institution decides to do about it.

## Backend-Owned Truth

The Veklom backend is the source of truth for customer and product reality:

- Users, tenants, workspaces, teams, MFA state, API keys, and vault/security events.
- Evaluations, subscriptions, activation state, cash-backed reserve, reserve debits, top-ups, and transaction ledger.
- Model runs, Playground runs, compare runs, pipeline tests, endpoint calls, deployments, provider/model status, request logs, monitoring, audit logs, and evidence bundles.
- Marketplace installs, buyer/vendor lifecycle events, usage, billing events, and compliance exports.

UACP must not invent or overwrite these facts. If backend state says no paid activation exists, UACP must not show paid revenue. If backend state says an endpoint failed, UACP must not show that endpoint as healthy.

## UACP-Owned Truth

UACP V3 is the source of truth for institutional state:

- Pillars, committees, agents, workers, worker roles, permissions, schedules, runs, heartbeats, and outputs.
- Council proposals, votes, escalations, governance decisions, skill registry, approved skills, quarantined skills, and archive records.
- Command Center institutional status, worker ownership, committee alignment, pillar health, policy posture, unresolved escalations, and historical lineage.

UACP decides ownership, classification, escalation, and archive lineage. It does not own product billing, customer access, or backend execution facts.

## Shared IDs

All cross-system records must preserve these IDs when available:

- `workspace_id`
- `tenant_id`
- `user_id`
- `event_id`
- `run_id`
- `plan_id`
- `audit_id`
- `evidence_id`
- `deployment_id`
- `endpoint_id`
- `worker_id`
- `committee_id`
- `pillar_id`
- `proposal_id`
- `archive_id`

Command Center links must use these IDs to move from backend evidence to UACP archive state without losing provenance.

## Backend Event Schema

Backend-to-UACP events use this normalized shape:

```json
{
  "event_id": "pipeline_run:run_123",
  "event_type": "pipeline.run",
  "source": "veklom_backend",
  "workspace_id": "ws_123",
  "tenant_id": "ws_123",
  "user_id": "user_123",
  "entity_type": "pipeline",
  "entity_id": "pipe_123",
  "severity": "info",
  "status": "succeeded",
  "timestamp": "2026-05-08T20:15:00Z",
  "payload": {
    "latency_ms": 36,
    "policy_result": "passed",
    "reserve_impact": "0.25",
    "audit_id": "aud_123"
  },
  "uacp": {
    "pillar_ids": ["execution", "governance", "archives"],
    "committee_ids": ["governance-evidence", "experience-assurance"],
    "worker_ids": ["ledger", "sentinel", "mirror"]
  }
}
```

## Backend APIs UACP Can Read

The first internal read surface is mounted under `/api/v1/internal/uacp` and guarded by `require_internal_operator`.

- `GET /api/v1/internal/uacp/summary`
- `GET /api/v1/internal/uacp/events`
- `GET /api/v1/internal/uacp/event-stream`
- `GET /api/v1/internal/uacp/workspaces`
- `GET /api/v1/internal/uacp/runs`
- `GET /api/v1/internal/uacp/deployments`
- `GET /api/v1/internal/uacp/billing`
- `GET /api/v1/internal/uacp/evidence`
- `GET /api/v1/internal/uacp/monitoring`
- `GET /api/v1/internal/uacp/security`

These endpoints are read-only. They expose backend truth to UACP with normalized event ownership hints.

## UACP APIs Backend Can Call

The current write surface for UACP/operator runtime state is:

- `POST /api/v1/internal/operators/runs`
- `POST /api/v1/internal/operators/watch`
- `POST /api/v1/internal/operators/workers/{worker_id}/heartbeat`

These routes write worker runs, heartbeats, and operator-watch evidence. They must remain internal-only.

## Command Center Data Model

The Command Center must display:

- Backend truth: users, signups, evaluations, paid activations, subscriptions, reserve, revenue, runs, endpoint calls, failed routes, evidence exports, security state, marketplace installs, and monitoring status.
- UACP interpretation: active workers, worker failures, committee activity, council votes, open proposals, open escalations, archive writes, skill approvals, institutional risk, and pillar health.

The UI rule is: `backend truth + UACP interpretation`. Never display institutional interpretation without the backend fact that triggered it.

## Archive Write Rules

UACP writes an archive record when:

- A worker run completes.
- A worker fails, is demoted, is promoted, or misses heartbeat.
- A council vote, escalation, proposal, or governance decision occurs.
- A backend event is classified as incident, compliance-relevant, billing-relevant, security-relevant, or customer-visible.
- A policy, skill approval, pricing rule, deployment state, or route integrity decision changes.

Archive entries must include source IDs, event type, worker/committee/pillar ownership, evidence pointers, timestamp, decision, and approving authority where applicable.

## Permission Boundaries

Backend can write:

- Product events, runs, usage, billing, evidence, workspace state, deployment state, security events, and marketplace state.

UACP can write:

- Plans, worker runs, worker decisions, council votes, proposals, escalations, archive records, recommendations, and incident classifications.

UACP must not directly mutate backend product state without explicit governed permission. Blocked without approval:

- Change pricing.
- Delete user data.
- Make repositories public.
- Change compliance claims.
- Rotate production secrets.
- Ship code.
- Change customer access or billing state.

Allowed governed actions:

- Open incident.
- Open issue.
- Request worker run.
- Pause a worker.
- Mark a route degraded.
- Recommend pricing review.
- Request evidence package.

## Never Fake Rules

The following must never be mocked, inferred, or cosmetically filled in:

- Revenue, paid users, subscriptions, cash-backed reserve, reserve deductions, top-ups, or transaction ledger.
- Live users, active runs, endpoint health, provider health, route success/failure, latency, costs, or usage.
- Audit IDs, evidence bundles, signed exports, archive writes, worker run status, council votes, or security events.
- Command Center worker state, unless it comes from UACP worker runs or heartbeats.

If source data is missing, show `unavailable`, the route name, and the timestamp. Do not show decorative metrics.

## Current V1 Event Ownership

- `ai.complete`: ledger, pulse, mirror.
- `request.failed`: sentinel, sheriff, pulse.
- `pipeline.run`: ledger, sentinel, mirror.
- `deployment.state`: sentinel, sheriff, glide.
- `billing.reserve`: mint, gauge, ledger.
- `security.audit`: bouncer, ledger, oracle.
- `workspace.created`: welcome, signal, mirror.
- `subscription.state`: mint, gauge.

This mapping is implemented in `backend/apps/api/routers/internal_uacp.py` and should be expanded only when a worker has a clear owner, permission boundary, evidence path, and escalation rule.
