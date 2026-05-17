# Veklom Sovereign AI Hub — Master State Audit

**Generated:** 2026-05-16
**Repos audited:** `byosbackened`, `uacpgemini`, `Perplexterminal`
**Live site:** https://veklom.com

---

## Repository Overview

### `byosbackened` (Primary — Veklom Platform)
| Item | Value |
|---|---|
| Framework | FastAPI (Python 3.11) |
| Frontend | React 18 / Vite / TypeScript / Tailwind CSS |
| Database | PostgreSQL + Redis + MinIO/S3 |
| Auth | JWT HS256 (access 60min, refresh 7d) |
| Payments | Stripe (LIVE mode), Connect planned |
| LLM | Ollama (qwen2.5) primary, Groq fallback, circuit breaker |
| Deploy | Coolify on Hetzner, Cloudflare CDN |
| API prefix | `/api/v1` |

### `uacpgemini` (Quantum UACP / GPC)
| Item | Value |
|---|---|
| Frontend | React 19 / Vite / Tailwind CSS 4 / Motion |
| Backend | Express 4 / Node.js / WebSockets |
| AI | Google Gemini API (`@google/genai`) |
| Surfaces | Intent Console, Execution Graph, Ops/Control Plane |

### `Perplexterminal`
| Item | Value |
|---|---|
| Status | Minimal — single `index.html` + README |
| Purpose | Perplexity-style terminal interface (early prototype) |

---

## What Works (✅)

### Backend (byosbackened)
- **Auth system** — login, register, refresh, MFA, password reset, API keys
- **Workspace** — tenant-scoped CRUD, settings, members (read)
- **Marketplace** — 891-line router: vendor create/onboard, listing CRUD, submit/review workflow, file upload (S3 presigned), evidence packages, orders, payments (Stripe checkout + PaymentIntent), payouts
- **Token Wallet** — balance, top-up via Stripe checkout, ledger entries
- **Subscriptions** — Stripe activation checkout (Founding $395, Standard $795, Regulated $2500, Enterprise custom), operating reserve model, webhook handler
- **Pipelines** — full CRUD + versioning + DAG execution with policy gates and billing
- **Deployments** — full CRUD + canary/blue-green + promote/rollback + live endpoint test
- **Billing** — cost allocation, billing reports, breakdown by project/client
- **Audit** — tamper-evident audit log with per-entry hash verification
- **Compliance** — regulation checks, evidence bundles
- **Demo pipeline** — public SSE streaming demo (rate-limited, no auth)
- **AI router** — unified `/v1/exec` with memory, circuit breaker, provider routing
- **Security suite** — zero-trust middleware, rate limiting, IDS, threat events
- **Monitoring** — metrics, health, alerts, Prometheus scrape
- **Edge/IoT** — MQTT, Modbus, SNMP, canary ingest
- **Support bot** — in-app AI support chat
- **UACP module** — MCP handshake middleware, Gemini provider, orchestration endpoints

### Frontend (workspace)
- **All 13 workspace routes wired** — Login, Overview, Playground, Marketplace, Models, Pipelines, Deployments, Vault, Compliance, Monitoring, Billing, Team, Settings
- **Playground** — SSE streaming demo with real-time output
- **Marketplace** — catalog browsing, listing detail, Stripe checkout
- **Billing** — wallet balance, top-up packs, transaction history
- **Vault** — API key issue/revoke
- **Monitoring** — audit trail with per-entry hash verification
- **Auth** — JWT login with auto-refresh, GitHub OAuth callback

### uacpgemini
- **Intent Console** — natural language → deterministic plans via Gemini
- **Execution Graph** — hybrid logic sequence visualization
- **Ops/Control Plane** — real-time runs, event logs, observability signals

---

## What's Broken / Missing (❌)

### Critical — Revenue Blocking
1. **Stripe Connect vendor payouts** — `vendors/onboard` creates Express account but destination charge splitting (platform fee) is not wired end-to-end. Vendors cannot receive automatic payouts.
2. **Referral system** — No referral table, no referral link generation, no tracking, no rewards. Zero viral loop.
3. **Pricing page** — Only `landing/pricing.html` exists (static). No dynamic 3-tier pricing wired to Stripe subscriptions on the frontend.

### High Priority — UX Gaps
4. **`GET /monitoring/overview`** — needs to return `OverviewPayload` shape (KPIs, routing utilization, spend rollup, recent runs, policy events). Frontend handles 404 gracefully but shows error banner.
5. **Team invite** — `POST /workspace/members/invite` not implemented. Invite button disabled.
6. **Onboarding wizard** — No post-signup onboarding flow. New users land on Overview with no guidance.
7. **Empty states** — Many list views show raw "no items" instead of warm messages with CTAs.
8. **Loading skeletons** — Not implemented on data-loading views.
9. **Toast notifications** — No success/error toasts on write operations.
10. **Mobile responsiveness** — Not tested at 375px breakpoint.

### Medium Priority — Growth Infrastructure
11. **Email automation** — Resend API key configured but no email sequences (welcome, activation, upgrade nudge, win-back).
12. **Analytics** — No PostHog or equivalent product analytics. No funnel tracking.
13. **SEO** — No meta tags optimization, no sitemap, no structured data on landing pages.
14. **Content/Blog** — No blog system or content pages.
15. **Vendor success flow** — No automated vendor welcome, no listing optimization guidance.

### Low Priority — Polish
16. **API docs** — OpenAPI/Swagger disabled in production (auth-gated). No public developer docs.
17. **Performance** — No Redis caching on GET endpoints, no DB indexes audit.
18. **Rate limiting** — Exists on middleware level but not fine-tuned per auth endpoint.
19. **Playground presets** — No preset demo prompts showcasing capabilities.
20. **Share/Deploy CTAs** — No "share this run" or "deploy this" buttons in playground.

---

## Infrastructure State

| Component | Status | Notes |
|---|---|---|
| Hetzner node | ✅ Live | Coolify deployment |
| PostgreSQL | ✅ Live | Production database |
| Redis | ✅ Live | Caching + Celery broker |
| MinIO/S3 | ✅ Live | Object storage for marketplace files |
| Stripe | ✅ Live mode | Secret key, publishable key, webhook secret configured |
| Ollama | ✅ Available | qwen2.5:1.5b primary model |
| Groq | ✅ Fallback | Circuit breaker auto-switches |
| Cloudflare | ✅ CDN | Worker + tunnel configured |
| Resend | ⚠️ Key set | No email sequences built |
| Sentry | ⚠️ DSN set | Client error reporting |

---

## Env Vars Required (from `.env.example`)

| Category | Key Vars | Status |
|---|---|---|
| Database | `DATABASE_URL`, `POSTGRES_*` | ✅ Production |
| Redis | `REDIS_URL`, `REDIS_PASSWORD` | ✅ Production |
| Auth | `SECRET_KEY`, `ENCRYPTION_KEY` | ✅ Production |
| Stripe | `STRIPE_SECRET_KEY`, `STRIPE_PUBLISHABLE_KEY`, `STRIPE_WEBHOOK_SECRET` | ✅ Live mode |
| LLM | `LLM_BASE_URL`, `GROQ_API_KEY` | ✅ Configured |
| S3 | `S3_ENDPOINT_URL`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY` | ✅ Configured |
| Email | `RESEND_API_KEY` | ✅ Set |
| GitHub OAuth | `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET` | ⚠️ Optional |
| Gemini | `GEMINI_API_KEY` | ⚠️ Optional |

---

## Frontend Route → Backend Endpoint Map

| Route | Status | Read | Write |
|---|---|---|---|
| `/login` | ✅ | — | `POST /auth/login`, `POST /auth/refresh` |
| `/overview` | ⚠️ | `GET /monitoring/overview` (404 handled) | — |
| `/playground` | ✅ | `GET /demo/pipeline/stream` (SSE) | — |
| `/marketplace` | ✅ | `GET /marketplace/listings` | `POST /marketplace/payments/create-checkout` |
| `/models` | ✅ | `GET /workspace/models` | `PATCH /workspace/models/{slug}` |
| `/pipelines` | ✅ | `GET /pipelines`, `GET /pipelines/runs/recent` | `POST /pipelines`, `POST /pipelines/{id}/execute` |
| `/deployments` | ✅ | `GET /deployments` | `POST /deployments`, promote/rollback |
| `/vault` | ✅ | `GET /auth/api-keys` | `POST /auth/api-keys`, `DELETE` |
| `/compliance` | ✅ | `GET /compliance/regulations` | `POST /compliance/check` |
| `/monitoring` | ✅ | `GET /audit/logs` | `GET /audit/verify/{id}` |
| `/billing` | ✅ | `GET /wallet/balance`, transactions, topup | `POST /wallet/topup/checkout` |
| `/team` | ⚠️ | `GET /admin/users` | invite disabled |
| `/settings` | ✅ | `GET /workspace/api-keys`, models, `/auth/me` | `PATCH /workspace/models/{slug}` |

---

## Agent Workforce Deployment Priority

### Sprint 1 (Days 1–4): Ship the Core
- Agent-001: Stripe Connect end-to-end vendor payouts
- Agent-002: Referral system with viral loop
- Agent-003: UX completion (overview endpoint, empty states, toasts, skeletons)
- Agent-004: Playground enhancements (presets, share, deploy CTA)
- Agent-005: Onboarding wizard
- Agent-006: API docs (public)
- Agent-007: Performance (Redis caching, DB indexes)
- Agent-008: Security hardening (rate limits, auth audit)

### Sprint 2 (Days 3–10): Vendor Acquisition
- Agent-010 to Agent-030: 20 vendor hunter agents across GitHub, HuggingFace, ProductHunt, IndieHackers, Reddit, X, LinkedIn
- Agent-031: Vendor success manager

### Sprint 3 (Days 3–14): User Acquisition
- Agent-040: SEO optimization
- Agent-041: Content creation
- Agent-042: Community engagement
- Agent-043: Paid growth
- Agent-044: Product Hunt launch

### Sprint 4 (Days 7–14): Retention & Revenue
- Agent-050: Pricing page + Stripe subscription tiers
- Agent-051: Referral activation
- Agent-052: Email automation (Resend sequences)
- Agent-053: Analytics (PostHog + Grafana)

### Sprint 5 (Ongoing): Daily Operations
- Agent-060: Support agent
- Agent-061: Monitoring agent
- Agent-062: Content calendar agent
