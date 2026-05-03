# Veklom Backend API Inventory

**Purpose.** Single source of truth for the Veklom Workspace frontend rebuild. Every frontend page maps to endpoints listed here. Progressively expanded as screens are wired.

## Core facts

| Item | Value |
|---|---|
| Framework | FastAPI (Python 3.11) |
| API prefix | `/api/v1` (from `core.config.settings.api_prefix`) |
| Auth | JWT HS256 · access 60min · refresh 7d |
| Deploy | Coolify on Hetzner · Postgres + Redis + MinIO/S3 |
| CORS | `veklom.dev`, `www.veklom.dev`, `app.veklom.dev`, `veklom.com`, `www.veklom.com` |
| Stripe | LIVE mode · Connect (destination charges) planned |
| LLM | Ollama (qwen2.5:1.5b) primary · Groq fallback · circuit breaker |
| Public demo | `/api/v1/demo/pipeline/stream` (SSE) · `/api/v1/edge/demo/infrastructure` (REST) |
| Top-level exec | `/v1/exec` (no api_prefix) |

## Router mount map (from `apps/api/main.py`)

All mounted at `/api/v1` unless noted.

### Governance & execution
- `auth` — login, register, refresh, MFA, password reset
- `workspace` — tenant-scoped workspace CRUD, settings, members
- `exec_router` — **top-level** `/v1/exec` · unified prompt execution with memory + circuit breaker
- `ai` — AI helpers (generate, extract, classify)
- `exec` → `demo_pipeline` · public SSE pipeline theater
- `routing` — provider routing config, circuit breaker state
- `token_wallet` — wallet balance, top-up, ledger entries
- `subscriptions` — Stripe subscription lifecycle (legacy; to be replaced by pricing_tier + reserve model)
- `billing` — invoices, payment methods
- `cost` — per-workspace cost rollups
- `budget` — budget caps, alerts
- `audit` — tamper-evident audit log reads
- `compliance` — policy packs, evidence bundles
- `privacy` — PHI/PII redaction rules
- `content_safety` — content moderation rules
- `explainability` — per-decision traces
- `insights` — workspace insights
- `suggestions` — workspace suggestions

### Marketplace
- `marketplace_v1` — **28KB file · primary marketplace endpoints** · listings, search, vendor, buyer, installs, reviews

### Infrastructure
- `edge_ingest`, `edge_mqtt`, `edge_control`, `edge_modbus`, `edge_snmp`, `edge_canary` — legacy protocol ingest + normalization + governed AI decisions
- `plugins` — plugin registry

### Security & operations
- `security_suite` — zero-trust status, threat events
- `monitoring_suite` — metrics, health, alerts
- `kill_switch` — emergency stop
- `admin` — superuser ops (users, workspaces, overrides)
- `support_bot` — in-app support chat
- `locker_security`, `locker_monitoring`, `locker_users` — LockerPhycer integration

### Utility
- `upload`, `transcribe`, `extract`, `export`, `search`, `job` — file + async job primitives
- `autonomous` — autonomous agent runs
- `metrics` — Prometheus scrape (no auth, no api_prefix)
- `health` — `/health` (no api_prefix)
- `resend_webhooks` — email webhook receiver

## Auth flow (observed)

```
POST /api/v1/auth/login          { email, password } → { access_token, refresh_token, token_type, expires_in }
POST /api/v1/auth/refresh        { refresh_token }  → { access_token, expires_in }
POST /api/v1/auth/register       { email, password, ... } → { user, access_token, refresh_token }
GET  /api/v1/auth/me             (Bearer)           → { user }
POST /api/v1/auth/logout         (Bearer)           → { ok }
```

## Environment variables (frontend-relevant)

- `VITE_VEKLOM_API_BASE` — build-time API base URL
- `window.__VEKLOM_API_BASE__` — runtime override (see `config.js`)
- `VITE_STRIPE_PUBLISHABLE_KEY` — Stripe.js client key
- `VITE_SENTRY_DSN` — client error reporting
- `VITE_ENABLE_DEMO_MODE` — toggles demo-only features

## Frontend → backend endpoint map (as shipped, PR #19)

All 13 workspace routes now wired to real backend endpoints. Legend: ✅ live and wired · ⚠ endpoint gap (frontend degrades gracefully) · 🟡 inspection-only (authoring/write flow ships next).

| Route | Status | Read endpoints | Write endpoints |
|---|---|---|---|
| `/login` | ✅ | — | `POST /auth/login` (JWT), `POST /auth/refresh` auto-rotation |
| `/overview` | ✅ ⚠ | `GET /monitoring/overview` (may need shaping on backend — frontend handles 404 cleanly) | — |
| `/playground` | ✅ | `GET /demo/pipeline/stream` (SSE, public, rate-limited) | — |
| `/marketplace` | ✅ | `GET /marketplace/listings`, `GET /marketplace/listings/{id}` | `POST /marketplace/payments/create-checkout` (wired, stripe-gated) |
| `/models` | ✅ | `GET /workspace/models` | `PATCH /workspace/models/{slug}` (toggle) |
| `/pipelines` | 🟡 | `GET /audit/logs` (framed as "pipeline runs") | — · authoring UI + `/pipelines` CRUD ship in paired PR |
| `/deployments` | 🟡 | `GET /workspace/models` (grouped by zone) | — · `/deployments` CRUD + promote/rollback ship next |
| `/vault` | ✅ | `GET /auth/api-keys` | `POST /auth/api-keys`, `DELETE /auth/api-keys/{id}` |
| `/compliance` | ✅ | `GET /compliance/regulations` | `POST /compliance/check` |
| `/monitoring` | ✅ | `GET /audit/logs` (filters by op_type) | `GET /audit/verify/{log_id}` (per-row hash verify) |
| `/billing` | ✅ | `GET /wallet/balance`, `GET /wallet/transactions`, `GET /wallet/topup/options` | `POST /wallet/topup/checkout` (redirects to Stripe) |
| `/team` | ✅ | `GET /admin/users` (403-aware — shows upgrade hint for non-admins) | — · invite flow ships with `/workspace/members/invite` next |
| `/settings` | ✅ | `GET /workspace/api-keys`, `GET /workspace/models`, `/auth/me` (via store) | `PATCH /workspace/models/{slug}` |

### Known backend gaps to address in paired PR
- `GET /api/v1/monitoring/overview` — should return the `OverviewPayload` shape in `frontend/workspace/src/types/api.ts` (KPIs, routing utilization, spend rollup, recent runs, policy events). Frontend currently handles absence via a clear error banner.
- `/api/v1/pipelines/*` — CRUD + `/execute` + `/versions`. Authoring UI is specced in `PipelinesPage.tsx`; flip from audit-ledger view to real pipeline objects when these land.
- `/api/v1/deployments/*` — CRUD + `/promote` + `/rollback`. `DeploymentsPage.tsx` shows fleet grouped by cloud zone; swap to real deployment records when available.
- `/api/v1/workspace/members/invite` — Team invite flow. Page is read-live today; invite button is disabled pending endpoint.

### Shipped commits (PR #19 — `codex/workspace-frontend`)
1. `feat(frontend): workspace scaffold` — Vite/React/TS/Tailwind + auth + Overview
2. `fix(frontend): typecheck script` — tsc --noEmit (verified: npm install + build + dev server all pass)
3. `feat(frontend): Playground SSE theater + Marketplace catalog`
4. `feat(frontend): Billing page — wallet, top-up packs, transactions`
5. `feat(frontend): Settings page — identity, API keys, model toggles`
6. `feat(frontend): Monitoring page — audit trail with per-entry hash verify`
7. `feat(frontend): Vault (API key issue/revoke) + Team (members list)`
8. `feat(frontend): Compliance (regs + check) + Models (fleet grouped by provider)`
9. `feat(frontend): Pipelines + Deployments pages — final 2 routes wired`
