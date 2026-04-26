# Deployment Status — 2026-04-26

## ✅ Done

### Infrastructure
- **Hetzner Veklom server** — `5.78.135.11` (CPX21 / `veklom-prod-1`)
- **Hetzner ECOBE engine server** — `5.78.153.146`
- Both servers running Coolify v4.0.0-beta.474, validated, Docker installed

### Cloudflare DNS (zone `veklom.com`)
- ❌ Old Vercel A record (`216.198.79.1`) — **deleted**
- ❌ Old www CNAME (`vercel-dns-017.com`) — **deleted**
- ✅ `veklom.com` CNAME → `veklom.pages.dev` (proxied)
- ✅ `www.veklom.com` CNAME → `veklom.pages.dev` (proxied)
- ✅ `api.veklom.com` A → `5.78.135.11` (DNS only — for Coolify Let's Encrypt)
- ✅ `engine.veklom.com` A → `5.78.153.146` (DNS only — for Coolify Let's Encrypt)
- 3 verification TXT records preserved (Google + OpenAI)

### Cloudflare Pages
- Project `veklom` — deployed from `backend/landing/`
- Custom domains `veklom.com` + `www.veklom.com` — **active**, cert from google
- Live URL: https://veklom.com → 200 OK, real landing page (not stale Vercel cache)

### Coolify — Veklom (5.78.135.11:8000)
- Project `veklom` (uuid `ikhfe95etvykb68j6uaveow7`, env `production` `hnto8jupq9sfzu09rfh3jfv9`)
- Postgres `veklom-postgres` — **running:healthy** (uuid `llwfyzhnft87bz6brddiax1z`)
  - Internal: `postgres://byos:WZk0…@llwfyzhnft87bz6brddiax1z:5432/byos_ai`
- Redis `veklom-redis` — **running:healthy** (uuid `v8vf3lw73fx9lw9xmbq1tvo5`)
  - Internal: `redis://default:NE7O3…@v8vf3lw73fx9lw9xmbq1tvo5:6379/0`

### Coolify — ECOBE (5.78.153.146:8000)
- Project `ecobe` (uuid `a4n432ko5n3hxaqm2y5elrn2`, env `production` `vg6wn1esvfjre9469kmroznn`)
- Postgres `ecobe-postgres` — **running:healthy** (uuid `irl8kcwktt6avmwn795nl5o2`)
  - Internal: `postgres://ecobe:q-k2g…@irl8kcwktt6avmwn795nl5o2:5432/ecobe_engine`
- Redis `ecobe-redis` — **running:healthy** (uuid `rcef75qpur2yedxpbdtj8feh`)
  - Internal: `redis://default:qRR4S…@rcef75qpur2yedxpbdtj8feh:6379/0`

### Secrets (gitignored)
- `.env.cloudflare` — CF token + account ID
- `.env.coolify.veklom` — Coolify API URL + token
- `.env.coolify.ecobe` — Coolify API URL + token
- `.env.veklom` — backend secrets (DB pw, Redis pw, encryption keys)
- `.env.co2routerengine` — engine secrets
- `.env.hetzner` — Hetzner API token
- `.env.stripe` — Stripe live + test keys
- SSH keypair: `~/.ssh/coolify_key` (private) + `coolify_key.pub` (public, installed on both Hetzner roots)
- SSH keypair: `~/.ssh/veklom-deploy` (original Hetzner provisioning key)

## ⏳ Remaining work

### 1. Deploy backend app to Veklom Coolify
- **Repo:** `https://github.com/reprewindai-dev/byosbackened` (branch `main`)
- **Build context:** `/backend`
- **Dockerfile:** `infra/docker/Dockerfile.api` (Python 3.11 / gunicorn / port 8000)
- **Domain:** `api.veklom.com` (Coolify auto-provisions Let's Encrypt cert — DNS already in place)
- **Env vars to set:**
  - `DATABASE_URL` = veklom-postgres internal URL (above)
  - `REDIS_URL` = veklom-redis internal URL (above)
  - `SECRET_KEY` = `b4c0287deb9db28ab149dac488202c4f0267ffe31d7f9cbf4e9e04996912a692`
  - `ENCRYPTION_KEY` = `ece6e19ad1dd15ee2098877772d2738cebeee16a073ad713b00c994073e6e273`
  - All Stripe keys from `.env.stripe`
  - All BYOS-specific config (Groq, Ollama, etc.) from `core/config.py` defaults
- **After deploy:** run `alembic upgrade head` migrations via Coolify terminal

### 2. Deploy ECOBE engine to ECOBE Coolify
- **Repo:** `https://github.com/reprewindai-dev/ecobe-engineclaude` (branch `codex/fix-do-deploys` or merge to main)
- **Dockerfile:** root `Dockerfile` (Node 22 / Next.js / port 8080)
- **Domain:** `engine.veklom.com`
- **Env vars:**
  - `DATABASE_URL` = ecobe-postgres internal URL
  - `DIRECT_DATABASE_URL` = same (Prisma needs both)
  - `REDIS_URL` = ecobe-redis internal URL
  - `INTERNAL_API_KEY` = `1907b50ea201022e99fb3be17fbda1e6b23d6d5822e656ef23b8381e0b792ee1`
  - `JWT_SECRET` = `44603d47698af48c5a7b06ee5a6d8feaafe8918ff04d8b8de5e73a3c73cc57dd`
  - `DECISION_API_SIGNATURE_SECRET` = `96c6275b3ce3407fe062bc6d770e09322423ba4543981210d1852e52fbbceb09`
  - `BUILDTIME_DATABASE_URL` (build-arg, can be the runtime URL)
- **After deploy:** run `npx prisma migrate deploy` via Coolify terminal

### 3. Repoint Stripe webhook
- Once `https://api.veklom.com/v1/stripe/webhook` resolves with valid SSL, update Stripe Dashboard → Developers → Webhooks endpoint URL.
- Verify with `python scripts/verify_stripe.py`.

### 4. Smoke tests (post-deploy)
- `curl https://api.veklom.com/health` → 200
- `curl https://api.veklom.com/status` → `{ "db_ok": true, "redis_ok": true, ... }`
- `curl https://engine.veklom.com/health` → 200
- `curl https://engine.veklom.com/internal/v1/health` → 200

## Why the app deploys are paused
The Coolify v4 API for creating applications from public Git repos with custom Dockerfile paths (`POST /api/v1/applications/public`) requires a `destination_uuid` field that isn't trivially exposed in the standalone-server API responses. Two clean options:

**Option A (UI, ~5 min per server):**
1. Open the Veklom Coolify → click into project `veklom` → "+ New Resource" → "Public Repository" → paste the GitHub URL.
2. Build Pack: Dockerfile. Base directory: `/backend`. Dockerfile location: `infra/docker/Dockerfile.api`. Port: `8000`.
3. Domain: `api.veklom.com`. Enable SSL.
4. Add the env vars listed above.
5. Click Deploy.
6. Repeat on ECOBE Coolify with the engine repo.

**Option B (API, more brittle):**
A follow-up automation pass with deeper Coolify v4 schema introspection. The remaining gap is small but worth getting right rather than guessing field names.

## Quick reference URLs
- Veklom Coolify: http://5.78.135.11:8000
- ECOBE Coolify: http://5.78.153.146:8000
- Cloudflare Pages dashboard: https://dash.cloudflare.com/17e4b29893d8c5315f39b929cb8dd960/pages/view/veklom
- Live site: https://veklom.com
