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

## Frontend → backend endpoint map (progressively expanded)

| Screen | Read endpoints | Write endpoints |
|---|---|---|
| Login | — | `POST /auth/login`, `POST /auth/register`, `POST /auth/refresh` |
| Overview | `GET /workspace/current`, `GET /cost/summary`, `GET /audit/recent`, `GET /routing/status`, `GET /monitoring/overview` | — |
| Playground | `GET /workspace/models`, `GET /workspace/sessions`, `GET /policy/active` | `POST /v1/exec` (SSE), `POST /audit/export` |
| Vault | `GET /workspace/secrets`, `GET /workspace/api-keys` | `POST /workspace/secrets`, `POST /workspace/secrets/{id}/rotate`, `DELETE /workspace/secrets/{id}` |
| Marketplace | `GET /marketplace/listings`, `GET /marketplace/categories`, `GET /marketplace/featured`, `GET /marketplace/trending`, `GET /marketplace/listings/{slug}` | `POST /marketplace/checkout`, `POST /marketplace/installs` |
| Team | `GET /workspace/members`, `GET /auth/mfa/status`, `GET /audit/access` | `POST /workspace/members/invite`, `PATCH /workspace/members/{id}/role`, `POST /auth/mfa/enable` |
| Compliance | `GET /compliance/frameworks`, `GET /compliance/evidence`, `GET /compliance/packs` | `POST /compliance/evidence/export` |
| Monitoring | `GET /monitoring/metrics`, `GET /monitoring/alerts`, `GET /security/events` | `POST /monitoring/alerts/{id}/ack` |
| Billing | `GET /billing/invoices`, `GET /subscriptions/current`, `GET /token-wallet/balance`, `GET /token-wallet/ledger` | `POST /token-wallet/topup`, `POST /subscriptions/cancel` |
| Settings | `GET /workspace/current`, `GET /workspace/integrations` | `PATCH /workspace/current`, `POST /workspace/integrations/{provider}/connect` |
