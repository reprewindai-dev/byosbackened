# VEKLOM — COMPLETE AGENT HANDOFF
## For: Windsurf / Devin
## Date: 2026-04-30
## From: Perplexity AI session
## Owner: Anthony (solo founder, Quinte West, Ontario, Canada)

---

## RULE #1 — READ BEFORE TOUCHING ANYTHING

Anthony does not touch code, terminals, or dashboards.
YOU do 100% of all work. If a human click is unavoidable, tell Anthony exactly:
- What to click
- Where it is
- What to paste
One instruction. Not a tutorial.

---

## WHAT THIS PRODUCT IS

**Veklom** — Multi-tenant AI ops backend. Sovereign AI gateway / private AI control plane.
**Tagline:** Run any AI model inside your perimeter with audit logs, budget controls, and policy enforcement.

**The repo:** `reprewindai-dev/byosbackened` (private) — this is the ONLY repo. Backend + docs, no separate frontend repo.

---

## LIVE URLS

| Surface | URL | Status |
|---|---|---|
| Landing / acquisition page | https://veklom.com | Live (Cloudflare Pages) |
| API | https://api.veklom.com | Live, returns 200 |
| Marketplace catalog | https://veklom.com/api/v1/listings | Live |
| Signup | https://veklom.com/signup/ | Live |
| CO2 Router engine | https://engine.veklom.com | Separate product, separate server |

---

## INFRASTRUCTURE

### Veklom Production Server
- **Provider:** Hetzner
- **IP:** 5.78.135.11
- **Server name:** veklom-prod-1
- **SSH:** `ssh -F NUL -i ~/.ssh/veklom-deploy root@5.78.135.11`
- **Coolify dashboard:** http://5.78.135.11:8000
- **Coolify app name:** `veklom-api`
- **Coolify project:** `veklom`
- **Postgres:** Running on this server via Coolify
- **Redis:** Running on this server via Coolify
- **Ollama:** Running as `veklom-ollama` container on Coolify network, model: qwen2.5:0.5b

### CO2 Router / ECOBE (SEPARATE — do not mix with Veklom)
- **IP:** 5.78.153.146
- **Server name:** co2routerengine-prod-1
- **SSH:** `ssh -F NUL -i ~/.ssh/veklom-deploy root@5.78.153.146`
- **Coolify app:** `ecobe-engine`
- **Coolify project:** `ecobe`
- **Coolify dashboard:** http://5.78.153.146:8000

### DNS / Frontend
- **veklom.com** → Cloudflare Pages (acquisition/landing page — the FRONTEND)
- **api.veklom.com** → Veklom API on 5.78.135.11
- **engine.veklom.com** → CO2 Router on 5.78.153.146

---

## REPO STRUCTURE (byosbackened)

```
byosbackened/
├── AGENT_CONTEXT.md          ← Master context file, always read first
├── backend/
│   ├── apps/
│   │   ├── api/
│   │   │   ├── main.py       ← FastAPI entrypoint, all route mounts
│   │   │   ├── deps.py       ← Dependency injection (DB, auth, current user)
│   │   │   ├── routers/      ← All API route handlers
│   │   │   │   └── auth.py   ← Register, login, refresh, MFA, API keys, GitHub OAuth
│   │   │   ├── schemas/      ← Pydantic schemas
│   │   │   └── middleware/   ← Middleware stack
│   │   ├── ai/               ← AI module
│   │   ├── plugins/          ← Plugin system
│   │   └── worker/           ← Background worker
│   ├── core/
│   │   ├── config.py         ← Settings, env loading
│   │   ├── auth.py           ← Re-export shim (real logic in deps.py)
│   │   ├── security.py       ← JWT + bcrypt primitives
│   │   ├── license.py        ← ✅ IMPLEMENTED: License enforcement, feature gates, tier checks
│   │   ├── redis.py          ← Redis client
│   │   └── redis_pool.py     ← Connection pooling
│   ├── db/
│   │   ├── models/           ← 30 SQLAlchemy models
│   │   └── session.py        ← SQLAlchemy engine (Postgres / SQLite fallback)
│   ├── scripts/
│   │   ├── bootstrap_prod.sh         ← Run once to verify Postgres+Redis
│   │   └── build_buyer_package.py    ← Builds buyer zip by tier
│   ├── license/
│   │   └── server.py         ← License server (NOT YET deployed to license.veklom.com)
│   ├── docker-compose.dev.yml
│   ├── docker-compose.prod.yml
│   ├── render.yaml
│   └── alembic.ini
└── docs/
```

---

## WHAT IS ALREADY IMPLEMENTED ✅

| Feature | File | Notes |
|---|---|---|
| Auth (register, login, logout, refresh) | `apps/api/routers/auth.py` | Full JWT + refresh token rotation |
| MFA (TOTP) | `apps/api/routers/auth.py` | Setup, verify, disable |
| GitHub OAuth | `apps/api/routers/auth.py` | Full flow with signed CSRF state |
| API key management | `apps/api/routers/auth.py` | Create, list, revoke |
| License enforcement | `core/license.py` | Tier gates, trial TTL, free fallback |
| Feature gating | `core/license.py` | `require_feature(tier, "feature_name")` |
| Stripe subscription | `apps/api/routers/subscriptions.py` | Team $12K/yr, Business $35K/yr, Enterprise custom |
| Stripe webhook | backend | Payment fail = instant key deactivation |
| Token wallet | `db/models/` | 50,000 free trial credits on registration |
| Admin bypass | `apps/api/middleware/entitlement_check.py` | Superuser skips all plan gates |
| Ollama proxy | via main.py | qwen2.5:0.5b live on Coolify |
| Bedrock proxy | `apps/api/` | JWT auth, wallet checks, token deduction, audit log |
| Marketplace catalog | `/api/v1/listings` | Public, live |
| Buyer package builder | `scripts/build_buyer_package.py` | `--tier [starter|pro|sovereign]` |
| S3 backup | `scripts/` | Daily cron, 7-day retention |
| License system | `backend/license/server.py` | Issue, activate, verify, deactivate |

---

## WHAT IS NOT DONE YET ⚠️ — ACTUAL TODO LIST

### PRIORITY 1 — MISSING FRONTEND PRICING PAGE
- The acquisition page is at veklom.com (Cloudflare Pages)
- **The pricing section is MISSING or not rendering** — Anthony cannot see pricing on the live site
- Pricing tiers:
  - **Team** — $12,000/year (DB enum: `starter`)
  - **Business** — $35,000/year (DB enum: `pro`)
  - **Enterprise** — Custom pricing, contact sales only
- Stripe checkout is wired in `apps/api/routers/subscriptions.py`
- Frontend needs a `/pricing` page or section calling the Stripe checkout endpoint
- **First step:** Locate the Cloudflare Pages source for veklom.com and find where pricing should render

### PRIORITY 2 — COOLIFY STABILITY
- Stray Coolify artifact for commit `9493aceb` is restart-looping next to the live `veklom-api` container
- Do NOT touch the routed `veklom-api` service — it is live and working
- Reconcile the stray artifact without disrupting live traffic
- Reconcile Alembic migration state in production after stability is confirmed

### PRIORITY 3 — LICENSE SERVER DEPLOY
- `backend/license/server.py` exists but is NOT deployed
- Needs its own deploy to `license.veklom.com`
- Can be a subdomain on existing Hetzner server (5.78.135.11) or separate VPS

### PRIORITY 4 — TRIAL KEY AUTO-ISSUANCE
- Token wallet gets 50k credits on signup (working)
- Trial license key issuance NOT wired end-to-end yet
- `core/services/trial_onboarding.py` has `issue_trial_license` and `send_trial_welcome`

### PRIORITY 5 — UPTIME MONITORING
- UptimeRobot (free) — instructions in `backend/README.md`
- Not set up yet

---

## PRICING MODEL (for frontend)

| Tier | Display Name | DB Enum | Price | Trial |
|---|---|---|---|---|
| Free | Free | `free` | $0 | No |
| Team | Team | `starter` | $12,000/year | 14 days (Stripe-managed) |
| Business | Business | `pro` | $35,000/year | 14 days (Stripe-managed) |
| Enterprise | Enterprise | `enterprise` | Custom | None — contact sales |

**Feature gates (from `core/license.py` → `FEATURE_MIN_TIER`):**
- **Free:** 100k requests/month, 3 vendor connections, 1 API key
- **Team+:** Unlimited requests, 20 API keys, multi-vendor routing, cost dashboard, budget controls, audit logs, RBAC
- **Business+:** SSO, content safety, data masking, GDPR exports, HIPAA controls, plugin execution, audit exports
- **Enterprise:** Custom endpoints, workspace admin, white-label, private deployment, annual review

---

## KNOWN ISSUES / TECH DEBT

- Previous agent fabricated 777ms P95 benchmark claims — FALSE. Real numbers in `backend/HONEST_AUDIT_REPORT.md`
- `CONSISTENCY_TESTING.md` and old `AUDIT_REPORT.md` contain fabricated numbers — do not reference
- `core/security.py` and `core/redis.py` shadow real implementations — dead code, safe to delete
- `PRODUCTION_READINESS_REPORT.md` is 0 bytes / empty
- GitHub access tokens stored plaintext in User row — should be Fernet-encrypted at rest before v1.0

---

## COMMIT FORMAT

Lowercase, descriptive, no fluff.
✅ `wire pricing page to stripe checkout`
❌ `Update pricing component to include new Stripe integration`

---

## KEY DOCS

| File | Purpose |
|---|---|
| `AGENT_CONTEXT.md` | Master context — always read first |
| `backend/DEPLOY_STATUS.md` | Infra map, SSH, Coolify |
| `backend/HONEST_AUDIT_REPORT.md` | Real benchmark numbers |
| `backend/PRICING_STRATEGY.md` | Full pricing rationale |
| `backend/STRIPE_GO_LIVE.md` | Stripe setup |
| `backend/CLOUDFLARE_TUNNEL_SETUP.md` | Cloudflare tunnel |
| `backend/USER_MANUAL.md` | 40KB full user manual |

---

## FIRST ACTION FOR NEW AGENT

1. Read `AGENT_CONTEXT.md` in full
2. Go to the Cloudflare Pages project for veklom.com — find where the pricing section lives
3. Implement the pricing page with the 3 tiers above
4. Push so it deploys live to veklom.com
5. Confirm with Anthony that pricing is now visible on the live site

That is the #1 blocker. Everything else is secondary.
