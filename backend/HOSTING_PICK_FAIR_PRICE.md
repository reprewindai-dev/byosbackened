# Veklom Hosting — Fair Price, No Vendor Trap

**Goal:** keep the backend "always on" without bleeding money to the major clouds
or getting locked into proprietary services.

**Decision rule:** start cheap. Move only when revenue justifies it. Never let a
hosting bill exceed 15% of MRR.

---

## TL;DR — pick one, in this order

| Stage | Provider | Monthly cost | Why |
|---|---|---:|---|
| **Day 1 (no customers yet)** | **Render.com** | **$25-40** | Push-button deploy, free SSL, free domain attach, repo is already wired with `render.yaml`. |
| **First 1-3 paying pilots** | **Hetzner Cloud + Coolify** | **$15-30** | German, transparent pricing, no surprise bills. ~5x compute per dollar vs AWS. |
| **3-10 paying tenants** | **DigitalOcean App Platform** | **$60-120** | Predictable, audited, US/EU regions, customer-friendly compliance posture. |
| **10+ tenants / enterprise** | **Fly.io** or **Hetzner dedicated** | **$200-500** | Multi-region, anycast, BYO-VPC story for customers. |

**You should pick Render today.** Reasons below.

---

## Detailed comparison (verified Apr 2026)

### 🥇 Render.com — RECOMMENDED FOR YOU TODAY

| | |
|---|---|
| **Price for our stack** | API ($25 standard, 2 CPU 2GB) + Postgres ($20 standard) + Redis ($10 starter) + Worker ($7 starter) = **$62/mo** |
| **Free tier?** | API and Postgres can run on free/$7 starter while testing. **$14/mo to start.** |
| **Already wired?** | YES — `render.yaml` is in the repo and provisions everything in one click. |
| **HQ / data residency** | US (Oregon, Virginia) + Frankfurt EU region. |
| **Hidden costs** | None significant. Bandwidth: 100 GB free, then $0.10/GB. |
| **Lock-in risk** | Low. It's just Docker containers and Postgres. Move anywhere in a day. |
| **Verdict** | ✅ Best balance of "easy + cheap + not slimy." Push the repo, click deploy. |

**To go live today:**
1. Push repo to GitHub.
2. https://render.com → New → Blueprint → point at the repo.
3. Render reads `render.yaml`, provisions everything.
4. Add secrets (`STRIPE_SECRET_KEY`, `OPENAI_API_KEY`, etc.) in dashboard.
5. Live URL in ~6 minutes. Attach `api.veklom.com` later.

### 🥈 Hetzner Cloud — CHEAPEST CREDIBLE

| | |
|---|---|
| **Price** | CX22 (2 vCPU, 4 GB RAM) = **€4.51/mo (~$5)**. Add managed Postgres €15/mo, Redis self-hosted in same VM, plus backups €0.91/mo = **~$22/mo total**. |
| **What you give up** | You manage the OS. Patch updates yourself. No one-click deploy. |
| **Fix for that** | Install **Coolify** (free, self-hosted Heroku-clone) → adds the click-deploy UX on top of Hetzner. |
| **HQ / data residency** | German company, German + Finnish + US data centers. EU customers will love this. |
| **Hidden costs** | None. Hetzner is famously transparent — they publish a calculator and the bill matches it. |
| **Verdict** | ✅ Cheapest reputable option. Best for once you have a couple pilots and want margin. Pair with Cloudflare in front for DDoS + caching. |

### 🥉 DigitalOcean App Platform

| | |
|---|---|
| **Price** | API basic-xs ($5) → professional-xs ($12) + Postgres ($15) + Redis ($15) = **~$45-60/mo** |
| **Pros** | Cleaner than AWS, US/EU/Asia regions, has a SOC 2 + HIPAA-ready posture you can resell. |
| **Cons** | App Platform has occasional cold-start quirks. Slightly more expensive than Render for similar specs. |
| **Verdict** | Solid alternative if you don't like Render's aesthetic. Both are honest pricing. |

### 🔻 Fly.io

| | |
|---|---|
| **Price** | $0 baseline, pay per second of machine time + RAM. ~$30-50/mo at our scale. |
| **Pros** | Multi-region anycast, machines spin up in milliseconds, great for a "deploy in your VPC" demo. |
| **Cons** | Pricing dashboard is confusing. Postgres on Fly was historically wobbly (improved in 2025). Recent capital raises = pricing pressure expected. |
| **Verdict** | Skip until you specifically need multi-region. |

### 🔻 Railway

| | |
|---|---|
| **Price** | $5/mo "Hobby" + usage. Realistic at our size = $30-60/mo. |
| **Pros** | Beautiful UX. |
| **Cons** | They keep changing pricing. Removed free tier mid-2023. Trust issues. |
| **Verdict** | Skip. Render is strictly better for the same money. |

---

## ❌ Avoid for now (the "slimy" tier you mentioned)

| | Why skip |
|---|---|
| **AWS** | Pricing requires a PhD. Egress fees ($0.09/GB out) destroy you when customers download anything. Reserved Instances + Savings Plans + Spot is a full-time job. **Use only when a customer demands it.** |
| **Azure** | Same as AWS, plus a worse dashboard, plus Microsoft sales pressure. |
| **GCP** | Cleaner pricing than AWS, but free tier traps + sudden charges are common. Cloud Run is genuinely good but watch the Cloud SQL bill. |
| **Heroku (Salesforce)** | Was $7/mo dyno; now $5/mo eco + $9/mo basic + $50/mo Postgres standard. Sold to Salesforce, prices keep rising. **Don't.** |
| **Vercel for backend** | Made for Next.js front-ends. Backends behind it are expensive and serverless-only. |

---

## "Always on" — what that actually means

"Always on" requires three layers, all of which are simple:

### 1. The host doesn't sleep
- Render starter API plan **does** sleep on inactivity. **Standard ($25)** does not.
- Hetzner / DO / Fly: never sleep, always running.
- ✅ **Action:** use Render Standard, not Starter, for the API service.

### 2. Auto-restart on crash
- Render: built-in. If the container exits, it restarts within seconds.
- Hetzner + Coolify: built-in (Docker `restart: always`).
- ✅ **Already configured** in `infra/docker/docker-compose.yml` (`restart: unless-stopped`).

### 3. Health-check + auto-redeploy on bad deploy
- Render: reads `healthCheckPath: /health` from `render.yaml`. ✅ **Already wired.**
- Hetzner + Coolify: configurable, default 30s.
- Health endpoint: `@/c:/Users/antho/OneDrive/Desktop/.windsurf/byosbackened/backend/apps/api/main.py`
  exposes `/health` and `/status`. Both work.

### 4. Self-healing inside the app (already built)
You already have this. Verified in the code:
- **Circuit breaker** at `@/c:/Users/antho/OneDrive/Desktop/.windsurf/byosbackened/backend/core/llm/circuit_breaker.py:45-114`:
  Ollama dies → trip → route to Groq → after 60s probe Ollama → close on success.
- **Budget kill-switch:** if a tenant burns through their daily cap, the
  middleware returns 429, doesn't crash anything else.
- **Rate-limit fallback:** if Redis dies, falls back to in-process limits, app stays up.

✅ **The self-healing the user mentioned is real and lives in the LLM router layer.**
What "always on" needs is the hosting layer to also auto-restart, which Render
and Coolify both do for free.

### 5. Status page (optional, nice for enterprise)
Free option: **BetterStack** (formerly Better Uptime) — free tier monitors `/health`
every 3 min and posts a public status page. Adds 5 minutes of work, looks
professional in vendor-security questionnaires.

---

## Costs at honest scale

| Stage | Monthly hosting | When to graduate |
|---|---:|---|
| Pre-revenue / pilot demos | **$25-40** (Render free Postgres + $25 API) | Once first paying pilot signs |
| 1-3 paying pilots | **$60-80** (Render full stack) | When P95 latency creeps over 1 second consistently |
| 3-10 tenants | **$120-200** (Render or Hetzner with Postgres replica) | When customer demands EU residency or HA |
| 10+ tenants / enterprise | **$400-800** (multi-region Hetzner or DO) | When ARR > $500k and customers ask for SLA credits |

**Rule of thumb:** keep hosting under **15% of MRR.** If you sign one $7,500/mo
pilot, you can spend up to $1,125/mo on infra and still be healthy. You will
spend ~$80.

---

## Action right now (today)

1. **Render.com** account → upload your ID for verification (Stripe-style KYC; required because of high fraud rate from new accounts; same one minute thing). ✅
2. Push the backend repo to GitHub (private repo is fine).
3. Render → New → Blueprint → select repo → click Apply.
4. While that's deploying, in the dashboard:
   - Set `STRIPE_SECRET_KEY` (live or test)
   - Set `STRIPE_WEBHOOK_SECRET` (live or test)
   - Set `OPENAI_API_KEY` if using GPT
   - Set `GROQ_API_KEY` if using the self-healing fallback
   - Set `CORS_ORIGINS` to `["https://veklom.com","https://www.veklom.com"]`
5. Once green, attach `api.veklom.com` in Render → Custom Domains.
6. Add CNAME in Cloudflare DNS pointing `api.veklom.com` → Render's URL.
7. Test: `curl https://api.veklom.com/health` → expect `{"status":"ok"}`.

**Total time:** 30-45 minutes. **Total cost month one:** ~$25.

---

_Last verified: 2026-04-26. Pricing across all providers shifts every 6-12 months. Re-check before any major commitment._
