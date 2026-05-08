# AGENT CONTEXT â€” READ THIS FIRST

This file is the single source of truth for any AI agent working on this codebase.
Read this entire file before doing anything else. No exceptions.

---

## Who Owns This

- **Founder:** Anthony (solo founder, Quinte West, Ontario, Canada)
- **Rule:** Agent does 100% of all work. Anthony does not touch code, terminals, or dashboards. If it requires a human click, document it here and ask once.

---

## Projects Overview

### 1. Veklom (`byosbackened` repo â€” THIS REPO)
- **What it is:** Multi-tenant AI ops backend. Sovereign AI gateway / private AI control plane.
- **Tagline:** Run any AI model inside your perimeter with audit logs, budget controls, and policy enforcement.
- **Live URL:** https://veklom.com (acquisition page), https://api.veklom.com (API)
- **Marketplace:** https://veklom.com/api/v1/listings â€” public, returns catalog
- **Signup:** https://veklom.com/signup/
- **Status:** Live. API returns 200. llm_ok: true. Free Evaluation gets run-count limits, not credits or tokens.

### 2. CO2 Router / ECOBE Engine (separate repo)
- **What it is:** Carbon-aware routing engine
- **Live URL:** engine.veklom.com
- **Server:** 5.78.153.146 (co2routerengine-prod-1 on Hetzner)
- **Coolify project:** ecobe, app: ecobe-engine
- **Completely separate infrastructure from Veklom**

---

## Infrastructure Map

### Veklom Production Server
- **Hetzner IP:** 5.78.135.11
- **Server name:** veklom-prod-1
- **SSH:** `ssh -F NUL -i ~/.ssh/veklom-deploy root@5.78.135.11`
- **Coolify app:** `veklom-api`
- **Coolify project:** `veklom`
- **Coolify dashboard:** http://5.78.135.11:8000
- **Postgres:** Running on this server (provisioned via Coolify)
- **Redis:** Running on this server (provisioned via Coolify)
- **Ollama:** Running as `veklom-ollama` container on Coolify network, model: qwen2.5:0.5b

### CO2 Router / ECOBE Production Server
- **Hetzner IP:** 5.78.153.146
- **Server name:** co2routerengine-prod-1
- **SSH:** `ssh -F NUL -i ~/.ssh/veklom-deploy root@5.78.153.146`
- **Coolify app:** `ecobe-engine`
- **Coolify project:** `ecobe`
- **Coolify dashboard:** http://5.78.153.146:8000
- **Postgres:** Running on this server
- **Redis:** Running on this server

### DNS / Frontend
- **Cloudflare Pages:** veklom.com (acquisition/landing page)
- **veklom.dev:** live Cloudflare Pages surface for acquisition and marketplace entry
- **api.veklom.com:** â†’ Veklom API on 5.78.135.11
- **engine.veklom.com:** â†’ CO2 Router on 5.78.153.146

---

## Current State â€” Veklom Backend

### What's Working âœ…
- `GET /health` â†’ 200
- `GET /status` â†’ llm_ok: true
- `GET /api/v1/listings` â†’ public marketplace catalog
- Signup at veklom.com/signup/ â†’ workspace created with Free Evaluation limits and $0.00 reserve balance
- API key creation via dashboard/API
- `POST /v1/exec` with X-API-Key â†’ verified against live Ollama (qwen2.5:0.5b)
- `POST /api/v1/ai/complete` -> governed AI execution with JWT auth, Free Evaluation limits, Operating Reserve debit, and audit logging
- Workspace dashboard tabs -> overview, AI playground, observability, API keys, models, and cost/budget
- Public `/status` page -> live uptime surface for API, Auth, Marketplace, and AI Proxy
- Hetzner backup automation -> S3 backup script, daily cron, and 7-day retention cleanup
- Admin/owner/superuser login â†’ full enterprise entitlement (no plan gates)
- License system: issue, activate, verify, deactivate, health endpoint
- Stripe webhook: payment fail = instant key deactivation
- Buyer package builder: `python backend/scripts/build_buyer_package.py --tier [starter|pro|sovereign] --version 1.0.0`
- Internal Builder Agents: `builder-scout`, `builder-forge`, and `builder-arbiter` registered in `/api/v1/internal/operators/workers` for clean-room marketplace tool research/build/release gating. Operating model: `docs/BUILDER_AGENTS.md`. Upstash Box/QStash readiness: `docs/UPSTASH_OPERATORS.md`.

### What's NOT Done Yet âš ï¸
- The newest Coolify build artifact for commit `9493aceb` is still restart-looping beside the live routed API container; keep the routed `veklom-api` service as the source of truth until Coolify is reconciled
- License server NOT deployed to its own VPS at license.veklom.com yet
- Trial key auto-issuance on signup not wired end-to-end yet
- UptimeRobot monitoring not set up yet (instructions are in backend/README.md)
- `DATABASE_URL` and `REDIS_URL` are present in the live Coolify service env; use bootstrap_prod.sh only when validating a future redeploy

### Known Issues / Tech Debt
- Previous agent fabricated 777ms P95 benchmark claims â€” those are false. Real numbers in `backend/HONEST_AUDIT_REPORT.md`
- `CONSISTENCY_TESTING.md` and old `AUDIT_REPORT.md` contain fabricated numbers â€” do not reference them
- Coolify has a stray app that built from main but is NOT routed to api.veklom.com â€” do not touch it, it's probably the CO2 router engine app
- `core/security.py` (file) and `core/redis.py` shadow real implementations â€” dead code, delete when safe

---

## Key Files

| File | Purpose |
|------|---------|
| `backend/DEPLOY_STATUS.md` | Infra map, SSH access, Coolify setup steps |
| `backend/HONEST_AUDIT_REPORT.md` | Real benchmark numbers, bug history |
| `backend/scripts/bootstrap_prod.sh` | Run once to verify/wire Postgres+Redis into Coolify |
| `backend/scripts/build_buyer_package.py` | Builds buyer zip (excludes server-side files) |
| `docs/BUILDER_AGENTS.md` | Clean-room Builder Agent operating model and Upstash Box experiment contract |
| `docs/UPSTASH_OPERATORS.md` | QStash schedules, Upstash operator guardrails, optional Builder Agent heartbeat |
| `backend/license/server.py` | License server (needs separate deploy to license.veklom.com) |
| `backend/apps/api/middleware/entitlement_check.py` | Admin bypass for plan gates |
| `backend/core/config.py` | Reads DATABASE_URL, REDIS_URL, all env vars |
| `backend/db/session.py` | SQLAlchemy engine â€” uses Postgres if URL is postgresql://, SQLite fallback |
| `backend/core/redis_pool.py` | Redis client â€” uses REDIS_URL |

---

## Agent Rules

1. **Always read this file first** on every new session.
2. **SSH key location:** `~/.ssh/veklom-deploy` on Anthony's local machine â€” agents in cloud environments cannot SSH directly. Use the Coolify API token if available, or push scripts that Anthony runs locally.
3. **Never document without implementing.** If it's supposed to work, it must be in code, not just in a markdown file.
4. **Never fabricate benchmark numbers.** If you run a test, output real numbers. If you can't run it, say so.
5. **Anthony does not touch code.** If you need a one-time human action (e.g. paste an env var into Coolify), tell him exactly what to paste, where, and why â€” one clear instruction, not a tutorial.
6. **Commit message format:** lowercase, descriptive, no fluff. Example: `wire postgres+redis env vars into coolify app`
7. **Kulafaya** â€” mentioned by Anthony, context unclear. Ask Anthony what Kulafaya is and add it to this file.

---

## Next Priorities (in order)

1. Reconcile the stray Coolify restart-looping artifact for commit `9493aceb`
2. Reconcile Alembic migration state in production
3. Deploy license server to license.veklom.com (separate Hetzner VPS or subdomain on existing server)
4. Wire trial key auto-issuance on workspace signup
5. Set up UptimeRobot (free) for uptime monitoring
6. Get first paying pilot customer
