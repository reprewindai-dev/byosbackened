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

## Frontend → backend endpoint map — 100% coverage

Legend: ✅ live and wired · ⚠ endpoint exists on backend but backend deploy pending · 🟡 inspection-only (write flow ships next)

### Original 13 workspace routes (PR #19)

| Route | Status | Read endpoints | Write endpoints |
|---|---|---|---|
| `/login` | ✅ | — | `POST /auth/login` (JWT), `POST /auth/refresh` auto-rotation |
| `/overview` | ✅ ⚠ | `GET /monitoring/overview` (404-aware) | — |
| `/playground` | ✅ | `GET /demo/pipeline/stream` (SSE, public, rate-limited) · `POST /cost/predict` · `POST /autonomous/quality/predict` | `POST /autonomous/quality/outcome` (learning loop) |
| `/marketplace` | ✅ | `GET /marketplace/listings`, `GET /marketplace/listings/{id}` | `POST /marketplace/payments/create-checkout` |
| `/models` | ✅ | `GET /workspace/models` | `PATCH /workspace/models/{slug}` |
| `/pipelines` | 🟡 | `GET /audit/logs` | — |
| `/deployments` | 🟡 | `GET /workspace/models` (grouped by zone) | — |
| `/vault` | ✅ | `GET /auth/api-keys` | `POST /auth/api-keys`, `DELETE /auth/api-keys/{id}` |
| `/compliance` | ✅ | `GET /compliance/regulations` | `POST /compliance/check` |
| `/monitoring` | ✅ | `GET /audit/logs` | `GET /audit/verify/{log_id}` |
| `/billing` | ✅ | `GET /wallet/balance`, `GET /wallet/transactions`, `GET /wallet/topup/options` | `POST /wallet/topup/checkout` |
| `/team` | ✅ | `GET /admin/users` | — |
| `/settings` | ✅ | `GET /workspace/api-keys`, `GET /workspace/models`, `/auth/me` | `PATCH /workspace/models/{slug}` |

### NEW routes — all 13 previously unwired router groups now wired

| Route | Hook(s) | Endpoints wired |
|---|---|---|
| `/routing` | `useRouting` | `GET /routing/providers` · `PATCH /routing/providers/{id}` · `GET /routing/circuit-breaker/status` · `POST /routing/circuit-breaker/{provider}/reset` |
| `/budget` | `useBudget` | `GET /budget/caps` · `POST /budget/caps` · `PATCH /budget/caps/{id}` · `DELETE /budget/caps/{id}` · `GET /budget/alerts` |
| `/security` | `useSecuritySuite` | `GET /security/zero-trust/status` · `GET /security/threats` · `PATCH /security/threats/{id}/resolve` · `GET /kill-switch/state` · `POST /kill-switch/activate` · `POST /kill-switch/deactivate` |
| `/privacy` | `usePrivacyAndSafety` | `GET /privacy/rules` · `POST /privacy/rules` · `PATCH /privacy/rules/{id}` · `DELETE /privacy/rules/{id}` |
| `/content-safety` | `usePrivacyAndSafety` | `GET /content-safety/rules` · `PATCH /content-safety/rules/{id}` · `GET /explainability/traces` · `GET /explainability/traces/{id}` |
| `/insights` | `useInsights` | `GET /insights` · `PATCH /insights/{id}/read` · `PATCH /insights/{id}/dismiss` · `GET /suggestions` · `PATCH /suggestions/{id}/respond` |
| `/plugins` | `usePlugins` | `GET /plugins` · `POST /plugins/{slug}/install` · `DELETE /plugins/{slug}` · `PATCH /plugins/{slug}` · `PATCH /plugins/{slug}/config` |
| `/jobs` | `useJobManager` | `GET /job` · `GET /job/{id}` (auto-poll) · `POST /job/{id}/cancel` · `POST /upload` · `POST /export` |
| Playground (enhanced) | `useAiHelpers` + `useExec` | `POST /ai/generate` · `POST /ai/extract` · `POST /ai/classify` · `POST /v1/exec` (no prefix) |
| Support chat (widget) | `SupportBotWidget` | `POST /support-bot/message` |

### Backend gaps still pending backend deploy

- `GET /api/v1/monitoring/overview` — OverviewPayload shape in `frontend/workspace/src/types/api.ts`
- `/api/v1/pipelines/*` — CRUD + `/execute` + `/versions`
- `/api/v1/deployments/*` — CRUD + `/promote` + `/rollback`
- `/api/v1/workspace/members/invite` — Team invite
- `POST /api/v1/autonomous/quality/outcome` — Learning loop receiver (Playground)
- Edge routers (`edge_ingest`, `edge_mqtt`, `edge_modbus`, `edge_snmp`, `edge_canary`) — no frontend surfaces needed unless LockerPhycer dashboard ships
