# Veklom Backend Capability Utilization Audit

Generated: 2026-05-05

## Objective

Find backend capabilities that already exist but are not fully surfaced, monetized, or wired into the current workspace frontend.

This audit is code-derived from:

- `backend/apps/api/main.py`
- `backend/apps/api/routers/`
- `backend/core/`
- `backend/edge/`
- `backend/license/`
- `backend/db/models/`
- `frontend/workspace/src/`

## Executive Finding

The backend contains materially more product than the workspace UI currently exposes.

Static inventory found:

- 42 backend router files.
- 206 router-declared endpoints before considering duplicate mount paths.
- 58 frontend API call sites.
- Roughly 45 distinct frontend-consumed API paths.
- Multiple commercial systems already present but underused: platform pulse, marketplace automation, edge protocol governance, status subscriptions, license issuance, autonomous optimization, workspace analytics, security suite, privacy/export, plugin-to-marketplace conversion, and cost/budget controls.

The competitive edge is real. The problem is not absence of backend code. The problem is productization: several backend capabilities are either invisible in the UI, only partially wired, using stale terminology, or not hardened enough to sell as-is.

## Critical Product Truth

Veklom no longer sells "usage credits" or generic "tokens" as the commercial unit.

Current business model:

- Free Evaluation: limited governed runs and compare runs.
- Activated workspace: one-time activation plus operating reserve.
- Reserve debited by event type.
- Governed run and compare run are commercial events.
- Evidence packs, auditor bundles, retention, exports, and compliance-grade artifacts are paid-only.

Any backend or frontend code using old "token", "credit", "monthly credits", or subscription-only language must be treated as legacy naming unless it refers to:

- JWT/auth tokens.
- LLM input/output token counts as technical telemetry.

## Backend Surface Map

Mounted backend areas include:

| Area | Routers / Services | Current frontend exposure | Utilization |
|---|---|---:|---|
| Auth / MFA / API keys / invite acceptance | `auth.py`, `workspace.py` | Login, register, accept invite, MFA, vault | Medium |
| AI completion / governed runs | `ai.py`, `exec_router.py`, `demo_pipeline.py` | Playground, landing demo | High |
| Workspace dashboard | `workspace.py`, `monitoring_suite.py` | Overview, top bar | Medium |
| Platform pulse / business metrics | `platform_pulse.py`, `financial_analytics.py` | Overview only | Low |
| Marketplace catalog / payment / vendor | `marketplace_v1.py`, `marketplace_catalog.py` | Marketplace browse, checkout, vendor create | Medium |
| Marketplace automation | `marketplace_automation.py` | Only preflight used | Low |
| Pipelines / deployments | `pipelines.py`, `deployments.py` | Pipelines, Deployments | Medium |
| Edge / legacy protocols | `edge/*`, `edge_canary.py` | Landing demo only, limited workspace exposure | Low |
| Cost / budget / billing allocation | `cost.py`, `budget.py`, `billing.py`, `kill_switch.py`, middleware | Playground preflight, Billing reserve | Low-Medium |
| Autonomous ML optimization | `autonomous.py`, `suggestions.py`, `core/autonomous/*` | Playground quality/risk only | Low |
| Security suite / Locker | `security_suite.py`, `locker_security.py`, `locker_monitoring.py`, middleware | No dedicated workspace page | Low |
| Privacy / GDPR / content safety | `privacy.py`, `content_safety.py` | Compliance page only partially related | Low |
| Status page subscriptions | `workspace.py`, `admin.py`, `status_updates.py` | Public status page likely, not workspace-admin complete | Medium |
| License server / buyer package control | `backend/license/*`, `trial_onboarding.py` | Signup/trial integration only | Low-Medium |
| Plugins | `plugins.py`, `apps/plugins/*` | Not surfaced | Low |
| Upload / transcribe / extract / search / export | `upload.py`, `transcribe.py`, `extract.py`, `search.py`, `export.py` | Not surfaced in workspace | Low |
| Support bot | `support_bot.py` | Not surfaced | Low |

## High-Value Hidden / Underused Capabilities

### 1. Platform Pulse + Superuser Business Metrics

Evidence:

- `backend/apps/api/routers/platform_pulse.py`
- `frontend/workspace/src/components/overview/PlatformPulseSection.tsx`
- `frontend/workspace/src/types/api.ts`

What exists:

- Public platform stats:
  - total users
  - users added in 30 days
  - active listings
  - listings added in 7 days
  - paid marketplace orders in 30 days
  - paid tier users
  - tier distribution
  - sanitized activity feed
- Superuser-only stats:
  - MRR
  - MRR delta
  - ARPU
  - 30-day churn
  - trial conversions
  - open security threats
  - past-due subscriptions
  - marketplace gross revenue

What is underused:

- The pulse appears on Overview, but not inside Marketplace where public proof matters most.
- There is no dedicated superuser operator page for business KPIs.
- It does not yet include governed run count, compare run count, reserve debits, evidence exports, or API activation counts.

Commercial value:

- High. This is the foundation for marketplace credibility and founder-only operating control.

Action:

- Surface the public subset on Marketplace.
- Create a superuser-only admin page for MRR, churn, marketplace gross, past-due, security threats, trial conversions, and run economics.
- Extend pulse with event-based run metrics from `TokenTransaction`, `WorkspaceRequestLog`, and `AIAuditLog`.

### 2. Marketplace Automation

Evidence:

- `backend/apps/api/routers/marketplace_automation.py`
- `frontend/workspace/src/pages/MarketplacePage.tsx`

What exists:

- `POST /api/v1/marketplace/listings/auto-classify`
- `POST /api/v1/marketplace/listings/auto-validate`
- `POST /api/v1/marketplace/listings/{listing_id}/install`
- `POST /api/v1/marketplace/listings/from-plugin`
- `POST /api/v1/marketplace/listings/import-github`
- `GET /api/v1/marketplace/featured`
- `GET /api/v1/marketplace/listings/{listing_id}/preflight`

What is underused:

- Frontend currently uses only preflight.
- The UI has "Install unavailable" states even though a real install endpoint exists for active `pipeline` and `agent` listings.
- Auto-classify, auto-validate, plugin-to-listing, and GitHub import are not surfaced.

Commercial value:

- Very high. This is a real marketplace loop:
  - vendor submits asset
  - system classifies it
  - system validates safety/privacy/cost
  - buyer installs it into their workspace as a real pipeline

Risk:

- The code imports `core.content_safety.scanner` and `core.privacy.detector`, but those exact modules appear inconsistent with existing code paths (`core/privacy/pii_detection.py` exists). The route soft-passes when unavailable, which is safe operationally but weak for trust if shown as "validated".

Action:

- Wire install flow for installable listings.
- Wire vendor auto-classify and auto-validate.
- Replace soft-pass validation notes with explicit UI copy.
- Ensure validation uses real existing scanner/detector modules.

### 3. Workspace Analytics / Observability

Evidence:

- `backend/apps/api/routers/workspace.py`
- `backend/core/services/financial_analytics.py`
- `backend/core/services/workspace_gateway.py`

What exists:

- `GET /api/v1/workspace/analytics/summary`
- `GET /api/v1/workspace/analytics/requests`
- `GET /api/v1/workspace/observability`
- financial usage summary
- request rows
- by-model costs
- by-path costs
- daily request and cost series
- latency fields from request logs

What is underused:

- Frontend does not call these analytics endpoints.
- Overview and Monitoring derive some stats from `monitoring/overview` and audit logs, but the richer analytics endpoints are mostly hidden.
- This is likely why latency and usage graphs feel incomplete even though backend structures exist.

Commercial value:

- High. This is the customer-facing proof that Veklom measures every governed run, model, path, cost, and latency.

Action:

- Wire Overview and Monitoring to workspace analytics.
- Use `workspace/analytics/requests?include_rows=true` for the "who ran what, when, model, cost, latency" table.
- Use `workspace/observability` for the performance/latency panels.

### 4. Platform Financial Analytics Service

Evidence:

- `backend/core/services/financial_analytics.py`
- `platform_financial_overview()`

What exists:

- Platform-wide MRR.
- ARR.
- active subscriptions.
- subscription starts/cancels.
- churn approximation.
- token pack/reserve revenue.
- request cost and volume.
- model-level cost.
- cost allocation.

What is underused:

- `platform_financial_overview()` is not referenced by any router.
- `platform_pulse.py` independently computes part of this, but the richer financial service is unused.

Commercial value:

- High for founder/superuser admin.

Action:

- Add a superuser-only `/api/v1/admin/financials` route.
- Build a founder-only admin page using this service.
- Keep these fields off public Marketplace and tenant dashboards.

### 5. Public Status Page + Email/Webhook/Slack Subscriptions

Evidence:

- `backend/apps/api/routers/workspace.py`
- `backend/core/services/status_updates.py`
- `backend/apps/api/routers/admin.py`
- `backend/db/models/status_subscription.py`

What exists:

- `GET /status/data`
- `GET /status/json`
- `GET /status/rss.xml`
- `POST /status/subscribe`
- `POST /api/v1/admin/status/incidents`
- subscriber delivery to email, Slack, and webhook
- encrypted subscriber target storage
- Slack webhook validation
- public routable webhook validation

What is underused:

- The status subscription feature is stronger than the current workspace surface indicates.
- Admin incident creation exists but needs a proper superuser UI.
- Status subscribe should be tested end-to-end from `veklom.com/status`.

Commercial value:

- Medium-high. This is trust infrastructure for regulated buyers.

Action:

- Verify `veklom.com/status` posts to `/status/subscribe`.
- Add superuser incident/maintenance controls.
- Show this as operational maturity, not as a placeholder status page.

### 6. Edge / Legacy Protocol Governance

Evidence:

- `backend/edge/routers/edge_ingest.py`
- `backend/edge/routers/snmp.py`
- `backend/edge/routers/modbus.py`
- `backend/edge/routers/mqtt.py`
- `backend/apps/api/routers/edge_canary.py`
- `backend/edge/services/protocol_canary.py`
- `backend/edge/services/legacy_targets.py`

What exists:

- public deterministic infrastructure demo
- HTTP webhook edge ingest
- SNMP allowlisted read and pipeline ingestion
- Modbus allowlisted read and pipeline ingestion
- public edge canary summary
- admin canary run
- protocol validation proof

What is underused:

- Workspace UI does not expose a proper "Edge / Legacy Infrastructure" product area.
- Marketplace can use these as real installable edge templates.
- MQTT router is explicitly stubbed: `501 MQTT connector pending`.

Commercial value:

- Very high. SNMP/Modbus-to-governed-AI is unusual and differentiates Veklom from generic LLM gateways.

Risk:

- MQTT must not be marketed as live until implemented.
- Live SNMP/Modbus must stay allowlisted to avoid SSRF/internal network exposure.

Action:

- Create Marketplace listings for "SNMP Governance Adapter", "Modbus Governance Adapter", and "Webhook Edge Ingest".
- Create a workspace Edge page or Deployments sub-panel.
- Keep MQTT labelled "pending" until implemented.

### 7. License Server / Buyer Package Control

Evidence:

- `backend/license/server.py`
- `backend/license/client_verifier.py`
- `backend/license/package_guard.py`
- `backend/license/server_signing.py`
- `backend/core/services/trial_onboarding.py`

What exists:

- standalone license server
- issue license
- activate license
- verify license
- deactivate license
- signed verification envelope
- machine fingerprint binding
- Stripe webhook hook for licensing
- package manifest guard
- trial license onboarding helper
- buyer download URL generation

What is underused:

- License server is not integrated into a visible paid-customer download flow in the workspace.
- There is no operator UI for issued licenses.
- Buyer download path needs to be verified against deployment.

Commercial value:

- Very high. This is how paying customers receive controlled backend access.

Action:

- Deploy license server if not already live.
- Add superuser license admin.
- Add activated-workspace download panel for eligible paid customers.
- Keep license keys out of public logs and UI after initial issuance.

### 8. Privacy, GDPR, PII, and Content Safety

Evidence:

- `backend/apps/api/routers/privacy.py`
- `backend/apps/api/routers/content_safety.py`
- `backend/core/privacy/*`
- `backend/core/safety/*`

What exists:

- GDPR export.
- GDPR delete.
- PII detect.
- PII mask.
- content metadata scan.
- file hash scan.
- age verification.
- content filter logs.

What is underused:

- Compliance page uses compliance checks but does not expose privacy tools directly.
- Playground policy has PHI/PII controls, but there is no visible PII redaction tool/workflow page.

Commercial value:

- High, but only if positioned correctly.

Risk:

- `content_safety.py` includes adult-platform language. That should not leak into Veklom's regulated-enterprise positioning unless intentionally sold to that market.
- GDPR delete is powerful and must stay behind confirmation and proper role checks.

Action:

- Rebrand general-use pieces as "Privacy Controls" and "PII/PHI Redaction".
- Expose PII detect/mask as tools inside Playground and Marketplace packs.
- Keep export/delete behind paid activation and admin confirmation.

### 9. Cost Intelligence, Routing Policy, Budgets, Kill Switches

Evidence:

- `backend/apps/api/routers/cost.py`
- `backend/apps/api/routers/routing.py`
- `backend/apps/api/routers/budget.py`
- `backend/apps/api/routers/billing.py`
- `backend/apps/api/routers/kill_switch.py`
- `backend/core/cost_intelligence/*`
- `backend/apps/api/middleware/budget_check.py`

What exists:

- cost prediction
- cost prediction history
- routing policy create/read
- routing decision test
- budget create/read/forecast
- client/project cost allocation
- billing report
- cost breakdown
- emergency kill switch with auto-restore

What is underused:

- Playground calls cost predict.
- The UI does not expose a full routing policy editor.
- Client/project billing allocation is not surfaced.
- Kill switch is not visible in Settings/Billing/Monitoring.

Commercial value:

- High. This supports per-client budgets, agency billing, and governed run economics.

Action:

- Add budget/routing/kill switch controls to Settings or a new Governance page.
- Add client/project allocation to Billing.
- Show hard-stop status prominently.

### 10. Autonomous Optimization and Suggestions

Evidence:

- `backend/apps/api/routers/autonomous.py`
- `backend/apps/api/routers/suggestions.py`
- `backend/core/autonomous/*`

What exists:

- ML cost prediction.
- ML routing selection.
- routing outcome learning loop.
- routing stats.
- quality prediction.
- quality optimization.
- failure risk prediction.
- workspace model training.
- proactive optimization suggestions.
- predictive cache, queue optimizer, traffic predictor, anomaly detector, autoscaler modules.

What is underused:

- Playground uses quality prediction and failure risk.
- Suggestions are not surfaced.
- Training, routing stats, savings reports, and optimization recommendations are not user-facing.

Commercial value:

- High for premium "governance autopilot" positioning.

Risk:

- Several modules may need data volume to be meaningful.
- Do not present ML predictions as proven until backed by actual workspace data.

Action:

- Surface suggestions as "Optimization Inbox".
- Show model confidence and "learning" state honestly.
- Keep training behind superuser/enterprise controls.

### 11. Security Suite / Locker Security

Evidence:

- `backend/apps/api/routers/security_suite.py`
- `backend/apps/api/routers/locker_security.py`
- `backend/apps/api/routers/locker_monitoring.py`
- `backend/apps/api/middleware/locker_security_integration.py`
- `backend/apps/api/middleware/request_security.py`
- `backend/core/security/*`

What exists:

- IDS-style middleware.
- request security tracking.
- rate limiting.
- security headers.
- security event logging.
- security dashboards.
- threat stats.
- controls toggles.
- alert summaries.
- detailed health.

What is underused:

- No dedicated Security page in workspace.
- Security data only appears partially through Platform Pulse superuser fields.

Commercial value:

- Medium-high for regulated buyers.

Risk:

- There are overlapping routers: `security_suite.py` and `locker_security.py`.
- Need one product-level Security Center, not duplicate surfaces.

Action:

- Consolidate into one workspace Security Center.
- Keep threat details tenant-scoped.
- Surface open threats to superuser only where cross-tenant.

### 12. Plugin System and Plugin-to-Marketplace Bridge

Evidence:

- `backend/apps/api/routers/plugins.py`
- `backend/apps/plugins/loader.py`
- `backend/apps/plugins/registry.py`
- `backend/apps/api/routers/marketplace_automation.py`

What exists:

- plugin discovery from `apps/plugins`
- plugin metadata loading
- enable/disable plugin per workspace
- plugin docs endpoint
- convert plugin into draft marketplace listing

What is underused:

- No workspace UI.
- Only example plugin exists.
- Registry is in-memory, not persisted.

Commercial value:

- Medium now, high later.

Risk:

- In-memory enablement will reset on process restart.
- Do not sell plugin enablement as durable until persisted.

Action:

- Add DB-backed plugin enablement table before selling.
- Surface plugin-to-listing for vendors after persistence is fixed.

### 13. AI Support Bot

Evidence:

- `backend/apps/api/routers/support_bot.py`

What exists:

- no-auth support chat
- IP rate limit
- prompt injection guardrails
- LLM fallback path
- support memory

What is underused:

- Not surfaced on landing or workspace.

Commercial value:

- Medium. Useful for reducing support load and increasing conversion.

Risk:

- The hardcoded prompt contains obsolete pricing and "token metering" copy:
  - `$7,500/mo`, `$18,000/mo`, `$45,000/mo`
  - "token metering"
- This must be fixed before exposing it.

Action:

- Update system prompt to current activation/reserve/event pricing.
- Add product-safe support widget after prompt correction.

### 14. Upload / Transcribe / Extract / Search / Export

Evidence:

- `backend/apps/api/routers/upload.py`
- `backend/apps/api/routers/transcribe.py`
- `backend/apps/api/routers/extract.py`
- `backend/apps/api/routers/search.py`
- `backend/apps/api/routers/export.py`

What exists:

- S3-compatible upload.
- Celery transcription job queue.
- extract/summarize/titles/hooks endpoint.
- SERP search endpoint.
- export job queue.

What is underused:

- No visible workspace UI.

Commercial value:

- Medium as workflow building blocks.

Risk:

- Upload requires S3/R2 settings.
- Transcribe/export require worker queue.
- Extract parser explicitly says stub in `_parse_extract_result`.
- Search requires SERP provider.

Action:

- Keep these as internal building blocks for pipelines.
- Do not expose as premium product features until dependencies are verified.

## Middleware / Monetization Alignment Issues

### Old token middleware still exists

Evidence:

- `backend/apps/api/middleware/token_deduction.py`
- `frontend/workspace/src/components/layout/TopBar.tsx`
- `frontend/workspace/src/pages/BillingPage.tsx`

What exists:

- `TokenDeductionMiddleware` deducts old token/credit amounts for many non-AI endpoints.
- Wallet APIs still expose `monthly_credits_included`, `monthly_credits_used`, `total_credits_purchased`, and `total_credits_used`.
- Frontend partially rewords this as reserve, but types and fields remain credit/token based.

Current safety:

- `POST /api/v1/ai/complete` is not in the static token-cost table, so the new governed-run event pricing should not be double-charged by this middleware.

Problem:

- Terminology and ledger semantics are inconsistent with the locked business model.

Action:

- Rename outward-facing wallet fields to reserve/run language.
- Convert endpoint costs into reserve units only if they are intentionally billable.
- Otherwise disable old token deduction for customer-facing routes.
- Keep technical token counts only as model telemetry.

### Entitlement plan names are old

Evidence:

- `backend/apps/api/middleware/entitlement_check.py`

Current names:

- starter
- pro
- sovereign
- enterprise

Current commercial names:

- Free Evaluation
- Founding
- Standard
- Regulated / Enterprise

Action:

- Add a compatibility mapping.
- Do not show old names publicly.
- Ensure route gates map to actual paid activation state and tier.

## Route Mounting Issue To Review

`marketplace_v1_router` is included twice:

- `app.include_router(marketplace_v1_router, prefix=settings.api_prefix)`
- `app.include_router(marketplace_v1_router, prefix=f"{settings.api_prefix}/marketplace")`

This means marketplace endpoints may be exposed both as:

- `/api/v1/listings`
- `/api/v1/marketplace/listings`

Frontend uses the `/api/v1/marketplace/*` shape.

Action:

- Confirm whether the unscoped `/api/v1/listings`, `/api/v1/vendors/*`, `/api/v1/orders/*`, `/api/v1/payments/*`, `/api/v1/payouts/*` routes are intentional.
- If not intentional, remove or redirect the duplicate mount after checking external clients.

## Outdated Documentation

Evidence:

- `backend/docs/ENDPOINT_INVENTORY.md` generated 2026-04-27.
- It misses newer routes like Platform Pulse, workspace analytics, status subscriptions, deployments, pipelines, and marketplace automation.
- It also still uses "Token Cost Reference".

Action:

- Treat this new audit as the current utilization map.
- Replace the old endpoint inventory with a generated endpoint inventory after route naming is cleaned.

## Do Not Surface Yet Without Fixes

| Capability | Reason |
|---|---|
| MQTT connector | Router returns 501 pending. |
| Plugin enablement | In-memory registry, not durable. |
| Support bot | Hardcoded obsolete pricing/token language. |
| Extract parser | Parser function says stub. |
| Upload/transcribe/export | Require S3/R2 and worker queue verification. |
| Marketplace auto-validation | Soft-passes missing scanners; must use real modules before trust claims. |
| Old token/credit middleware | Misaligned with governance-run reserve pricing. |

## Highest-ROI Build Order

### P0 - Immediate revenue and trust

1. Wire public Platform Pulse into Marketplace.
2. Create superuser admin business dashboard using Platform Pulse + `platform_financial_overview()`.
3. Wire workspace analytics/observability into Overview and Monitoring for real latency/run/cost graphs.
4. Rename public wallet/credit/token language to operating reserve and governed runs.
5. Surface marketplace install flow for active pipeline/agent listings.

### P1 - Competitive edge surfacing

6. Build Marketplace vendor automation UI: auto-classify, auto-validate, import GitHub, plugin-to-listing.
7. Build Edge / Legacy Infrastructure page or Marketplace packs for SNMP, Modbus, and webhook governance.
8. Add Security Center from Locker/Security Suite.
9. Expose Privacy/PII tools as locked paid controls and marketplace packs.
10. Build status admin incident controls and verify Slack/webhook/email subscriptions.

### P2 - Product hardening

11. Persist plugin enablement in DB.
12. Fix support bot prompt and expose support widget.
13. Verify R2/S3 + Celery paths before exposing upload/transcribe/export.
14. Implement MQTT or remove it from public copy.
15. Regenerate endpoint inventory and remove duplicate marketplace route mount if not intentional.

## Bottom Line

The backend has a bigger competitive edge than the UI currently shows.

The strongest hidden assets are:

1. Marketplace automation that can turn a listing into a real installed pipeline.
2. Platform Pulse with public marketplace proof and private superuser business metrics.
3. Workspace analytics capable of real latency/run/cost dashboards.
4. Edge SNMP/Modbus governance, which is unusual for an AI gateway.
5. License server and signed package control for paid backend customers.
6. Autonomous cost/quality/routing optimization.
7. Security/Locker monitoring and incident infrastructure.
8. Status subscriptions with email, webhook, and Slack delivery.

The immediate risk is not that the backend lacks value. The risk is that some of the value is hidden, and some old BYOS/token/subscription language is still mixed into production paths.

Fix the language and surface the strongest systems. Do not fake usage. Use the real pulse, real runs, real listings, real reserve debits, and real install events.
