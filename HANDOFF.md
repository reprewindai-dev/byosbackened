# Veklom Handoff Document — Complete Context for Windsurf/Devin

**Status**: Ready for continuation  
**Last Updated**: 2026-05-11  
**Agent Rule**: Read this entire file before any work. No exceptions.

---

## Infrastructure

### Servers (Current IPs from AGENT_CONTEXT.md)

| Server | IP | Purpose | Status |
|--------|-----|---------|--------|
| Hetzner Server 1 | **5.78.135.11** | Production: Coolify + API + Ollama | ✅ Live |
| Hetzner Server 2 | **5.78.153.146** | CO2 Router / ECOBE Engine (can host license server) | ✅ Live |

**SSH Access:** `ssh -i ~/.ssh/veklom-deploy root@<IP>`

**Coolify Dashboards:**
- Server 1: `http://5.78.135.11:8000` (veklom project)
- Server 2: `http://5.78.153.146:8000` (ecobe project)

### DNS Routing

| Domain | Target | Status | Notes |
|--------|--------|--------|-------|
| `veklom.com` | Cloudflare Pages | **🔴 NEEDS DEPLOY** | pricing.html ready |
| `api.veklom.com` | 5.78.135.11 | ✅ Live | veklom-api container |
| `license.veklom.com` | 5.78.153.146 | ✅ Live | License service deployed and healthy |
| `veklom.dev` | Cloudflare Pages | ✅ Live | Acquisition surface |
| `engine.veklom.com` | 5.78.153.146 | ✅ Live | CO2 Router |

### Coolify Apps

- **Project:** `veklom`
- **App:** `veklom-api` (live container: `zjhp30ys1jlk8yaoxc96h2zd-194651611479`)
- **Resources:** PostgreSQL + Redis (both on 5.78.135.11)
- **Ollama:** `veklom-ollama` container with `qwen2.5:0.5b` model

**⚠️ CRITICAL:** The old `9493aceb` note was stale. The current non-routed restart-looping artifact is `lcile2sz1wjd6sqsdctlm4rv-033401126260`, built from commit `9636805d`. **DO NOT touch live service** — investigate separately.

---

## Repository Structure

```
byosbackened/
├── backend/                    # Main FastAPI application
│   ├── apps/api/routers/       # All API endpoints
│   │   ├── subscriptions.py    # PLANS dict (cents) ⭐ KEEP IN SYNC
│   │   ├── auth.py            # Registration + trial license trigger
│   │   ├── stripe_billing.py  # Stripe integration
│   │   └── ...
│   ├── core/services/
│   │   └── trial_onboarding.py  # Trial license HTTP client
│   ├── license/                # License server code
│   │   ├── server.py          # FastAPI license server (to deploy)
│   │   ├── stripe_webhook.py  # Payment failure → deactivation
│   │   ├── validator.py       # License verification logic
│   │   └── middleware.py      # FastAPI license middleware
│   ├── db/models/subscription.py  # PlanTier enum
│   ├── core/config.py          # Environment variables
│   └── PRICING_TRUTH.md        # ⭐ Authoritative pricing reference
├── landing/
│   └── pricing.html            # ✅ Public pricing page (ready to deploy)
├── AGENT_CONTEXT.md            # Historical context
└── HANDOFF.md                  # This file
```

---

## Pricing (Single Source of Truth)

### Public Pricing

No subscriptions. No tokens. Reserve balances are USD-denominated and never expire.

| Tier | DB Enum | Activation | Minimum Reserve | Display Name |
|------|---------|------------|-----------------|--------------|
| Free Evaluation | n/a | $0 | $0 | Evaluate |
| Founding | `starter` | $395 one-time | $150 | Founding Activation |
| Standard | `pro` | $795 one-time | $300 | Standard |
| Regulated | `sovereign` | From $2,500 | $2,500 | Regulated |
| Enterprise | `enterprise` | Private terms | Private terms | Enterprise |

Free Evaluation is limited by run counts: 15 governed Playground runs, 3 compare runs, 20 policy tests, 2 watermarked exports, BYOK provider testing, and marketplace browsing.

### Files to Keep in Sync

| Location | File Path | Must Show |
|----------|-----------|-----------|
| Backend PLANS dict | `backend/apps/api/routers/subscriptions.py:23-147` | Activation cents and minimum reserve cents |
| Human reference | `backend/PRICING_TRUTH.md` | All tiers with explanations |
| Public page | `landing/pricing.html` | Cards, JSON-LD, FAQ |
| Structured data | `veklom_landing_reference.html` | JSON-LD SoftwareApplication |
| Stripe Dashboard | Manual setup | One-time activation Checkout plus Operating Reserve funding |

### Current PLANS Dict Reference (subscriptions.py)

```python
"starter": {"name": "Founding Activation", "activation_cents": 39_500, "minimum_reserve_cents": 15_000}
"pro": {"name": "Standard Activation", "activation_cents": 79_500, "minimum_reserve_cents": 30_000}
"sovereign": {"name": "Regulated Activation", "activation_cents": 250_000, "minimum_reserve_cents": 250_000, "self_serve_checkout": False}
```

---

## Priority TODO (In Order)

### 🔴 #1: Pricing Page on veklom.com

**Status:** `landing/pricing.html` is complete and ready  
**Action:** Deploy to Cloudflare Pages

```bash
cd C:\Users\antho\OneDrive\Desktop\.windsurf\byosbackened\landing
wrangler pages deploy . --project-name=veklom-pricing
```

**After deploy:**
1. Cloudflare Pages dashboard → veklom-pricing → Custom domains
2. Add `veklom.com` as custom domain
3. Ensure DNS record points to Cloudflare Pages

---

### 🟡 #2: Coolify Stray Artifact Restart Loop

**Status:** Known issue, root cause confirmed  
**Action:** **DO NOT touch live service** — investigate only

**Details:** The current failed artifact is `lcile2sz1wjd6sqsdctlm4rv-033401126260`, built from commit `9636805d`, and it is restart-looping beside the routed `veklom-api` container. The live service at `api.veklom.com` is healthy.

**Investigation (safe):**
```bash
pwsh ./backend/scripts/inspect_production_reconcile.ps1
```

Do NOT stop, remove, or modify any containers without explicit direction.

---

### 🟡 #3: License Server Deploy

**Status:** Deployed on 2026-05-10 and healthy  
**Action:** Keep it healthy; use canonical `/api/licenses/*` URLs in config

**License server file:** `backend/license/server.py`

**Available endpoints:**
- `POST /issue` and `POST /api/licenses/issue` — Issue new license (admin only, X-Admin-Token required)
- `POST /activate` — Activate license on machine
- `POST /verify` and `POST /api/licenses/verify` — Verify license validity
- `POST /deactivate` — Deactivate license (admin only)
- `GET /health` — Health check
- `POST /stripe/webhook` — Stripe payment failure handling

**Deployment Options:**

**Option A: Hetzner Server 2 (Recommended for isolation)**
```bash
# Server 2 already exists (5.78.153.146)
# Add DNS: license.veklom.com → 5.78.153.146
ssh root@5.78.153.146
git clone <repo>
cd byosbackened/backend
pip install -r requirements.txt
# Set env vars (see below)
python -m license.server  # Runs on :8000
```

**Option B: New dedicated VPS**
- Create $5-10/mo Hetzner VPS
- Same setup as Option A

**Required env vars for license server:**
```bash
DATABASE_URL=postgresql://...  # Can share main DB or separate
LICENSE_ADMIN_TOKEN=vladmin_$(openssl rand -hex 32)
ENCRYPTION_KEY=$(openssl rand -hex 32)
APP_VERSION=1.0.0
# Optional for Stripe webhooks:
STRIPE_WEBHOOK_SECRET=whsec_...
```

---

### 🟡 #4: Trial Key Auto-Issuance

**Status:** Fixed and verified live on 2026-05-10  
**Action:** Backfill any pre-fix workspaces that should have trial metadata

**Current implementation:**

1. **Registration trigger** (`backend/apps/api/routers/auth.py:179-186`):
```python
license_payload = await issue_trial_license(
    db=db,
    workspace=workspace,
    user_email=payload.email,
    user_name=payload.full_name or payload.workspace_name,
    requested_tier=payload.trial_tier,  # "starter", "pro", etc.
)
```

2. **License client** (`backend/core/services/trial_onboarding.py:53-114`):
   - POSTs to `LICENSE_ISSUE_URL` (use canonical `https://license.veklom.com/api/licenses/issue`)
   - Requires `X-Admin-Token` header
   - 14-day trial duration

3. **Welcome email** (`backend/core/services/trial_onboarding.py:117-133`):
   - Sends license key + download link
   - Uses `buyer_download_base_url` for package URL

**Latest proof:**
- On 2026-05-10, a fresh production `/api/v1/auth/register` signup created workspace `Smoke License 1662` with `license_tier=starter` and a populated `license_key_prefix`.

**Testing steps (for future regression checks):**
```bash
# 1. Register with trial tier
curl -X POST https://api.veklom.com/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test123","workspace_name":"Test","trial_tier":"starter"}'

# 2. Verify workspace has license
curl https://api.veklom.com/api/v1/admin/workspaces \
  -H "Authorization: Bearer <admin_token>"

# 3. Test license verification
curl -X POST https://license.veklom.com/api/licenses/verify \
  -H "Content-Type: application/json" \
  -d '{"license_key":"vklm_...","machine_fingerprint":"test-fingerprint"}'
```

---

### 🟡 #5: UptimeRobot Monitoring

**Status:** Not configured  
**Action:** Set up free monitoring

**Monitors to create:**

| Monitor | URL | Check |
|---------|-----|-------|
| 1 | `https://veklom.com` | HTTPS, keyword: "Veklom" |
| 2 | `https://api.veklom.com/health` | HTTPS, keyword: `"status":"ok"` |
| 3 | `https://license.veklom.com/health` | HTTPS (after deploy) |

**Steps:**
1. Sign up at uptimerobot.com (free tier: 50 monitors)
2. Add HTTP(s) monitors with 5-minute intervals
3. Configure alert contacts (email → Anthony)

---

## Working Features (Confirmed Live)

| Feature | Status | Endpoint/Location |
|---------|--------|-------------------|
| Health check | ✅ | `GET /health` → `{"status":"ok"}` |
| Status dashboard | ✅ | `GET /status` → includes `llm_ok: true` |
| Authentication (JWT, MFA, GitHub OAuth) | ✅ | `/api/v1/auth/*` |
| Stripe billing (checkout, portal, webhooks) | ✅ | `/api/v1/subscriptions/*` |
| License gates | ✅ | Token wallet middleware |
| Ollama proxy | ✅ | `POST /v1/exec` |
| Marketplace | ✅ | `GET /api/v1/listings` |
| Free Evaluation run limits | ✅ | 15 governed Playground runs, 3 compare runs, 20 policy tests, 2 watermarked exports |
| Admin bypass for plan gates | ✅ | `entitlement_check.py` |

---

## Environment Variables

### Production (Coolify)

```bash
# Database & Redis
DATABASE_URL=postgresql://postgres:...@postgres:5432/veklom
REDIS_URL=redis://redis:6379/0

# Stripe (LIVE keys)
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PUBLISHABLE_KEY=pk_live_...

# License server (main API calls this)
LICENSE_SERVER_URL=https://license.veklom.com
LICENSE_ISSUE_URL=https://license.veklom.com/api/licenses/issue
LICENSE_VERIFY_URL=https://license.veklom.com/api/licenses/verify
LICENSE_ADMIN_TOKEN=vladmin_...  # Must match license server

# Security
SECRET_KEY=...
ENCRYPTION_KEY=...

# LLM (Ollama on same server via Docker network)
LLM_BASE_URL=http://veklom-ollama:11434
LLM_MODEL_DEFAULT=qwen2.5:0.5b

# AWS (for Bedrock proxy)
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_DEFAULT_REGION=us-east-1

# Optional
SENTRY_DSN=
SMTP_HOST=  # For trial welcome emails
BUYER_DOWNLOAD_BASE_URL=  # S3 or CDN for buyer packages
```

### License Server (separate)

```bash
DATABASE_URL=postgresql://...  # Can share main or separate
LICENSE_ADMIN_TOKEN=vladmin_$(openssl rand -hex 32)  # 64-char hex
ENCRYPTION_KEY=$(openssl rand -hex 32)
APP_VERSION=1.0.0
STRIPE_WEBHOOK_SECRET=whsec_...  # Optional
```

---

## Key File Reference

| File | Purpose | Lines of Interest |
|------|---------|-------------------|
| `backend/apps/api/routers/subscriptions.py` | Plan catalog, checkout, webhooks | 23-147 (PLANS dict) |
| `backend/apps/api/routers/auth.py` | Registration + trial trigger | 179-186, 196-203 |
| `backend/core/services/trial_onboarding.py` | Trial license HTTP client | 53-133 |
| `backend/license/server.py` | License server FastAPI app | All |
| `backend/license/validator.py` | License verification | All |
| `backend/license/middleware.py` | License gates | All |
| `backend/core/config.py` | Environment variables | All |
| `backend/PRICING_TRUTH.md` | Pricing source of truth | All |
| `landing/pricing.html` | Public pricing page | All |

---

## Deployment Commands

### Cloudflare Pages (Pricing Page)
```bash
cd C:\Users\antho\OneDrive\Desktop\.windsurf\byosbackened\landing
wrangler pages deploy . --project-name=veklom-pricing
```

### Coolify (Backend)
- Auto-deploys on git push to main
- Manual: Coolify dashboard → Deploy

### License Server (Manual)
```bash
ssh root@5.78.153.146  # Or new VPS
cd /opt/veklom-license
git pull
pip install -r requirements.txt
# Set env vars in systemd service or .env
systemctl restart veklom-license
```

---

## Quick Health Checks

```bash
# Main API
curl https://api.veklom.com/health
curl https://api.veklom.com/status

# License server (after deploy)
curl https://license.veklom.com/health
```

---

## Commit Format Rules

```
<type>: <short description>

- feat: new feature
- fix: bug fix
- docs: documentation
- refactor: code restructuring
- deploy: deployment-related
```

Examples:
- `feat: add enterprise plan to pricing page`
- `fix: correct yearly cents calculation in PLANS`
- `deploy: license server to Hetzner Server 2`

---

## Support

- **Docs:** https://docs.veklom.com
- **API:** https://api.veklom.com/api/v1/docs
- **Admin Access:** Contact Anthony for Hetzner/Coolify credentials
- **SSH Key:** `~/.ssh/veklom-deploy` on Anthony's machine

---

## ⚠️ Critical Rules

1. **DO NOT** touch the live Coolify service — stray artifact under investigation
2. **DO NOT** modify pricing in only one place — sync all 4 locations
3. **DO NOT** commit secrets — use Coolify env var UI
4. **Always** test trial flow after license server deploy
5. **Always** run `alembic upgrade head` after schema changes
6. **Never** fabricate benchmark numbers
7. **Never** document without implementing

---

*Next Agent: Start with 🔴 #1 — deploy pricing page, then proceed in order.*
