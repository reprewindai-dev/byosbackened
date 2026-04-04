# GoonVault — Deploy to veklom.dev
## You do the steps marked 👤. Everything else is already built.

---

## PART 1 — Push Code to GitHub (do this first, on your PC)

### 👤 Step 1 — Open a terminal in this folder
In Windsurf: open the terminal (Ctrl + `) and make sure you're in:
```
c:\Users\antho\.windsurf\byosbackened\WindSurf-Repo
```

### 👤 Step 2 — Create a GitHub repo
1. Go to https://github.com/new (logged in as reprewindai@gmail.com)
2. Name it: `goonvault` (or any name you want)
3. Set to **Private** ← important (keeps your keys off public internet)
4. Click **Create repository**
5. Copy the repo URL — it looks like: `https://github.com/reprewindai/goonvault.git`

### 👤 Step 3 — Push your code (run these in terminal)
```powershell
git init
git add .
git commit -m "Initial GoonVault deploy"
git branch -M main
git remote add origin https://github.com/reprewindai/goonvault.git
git push -u origin main
```
> If it asks for login, use your GitHub email + a Personal Access Token from:
> https://github.com/settings/tokens → Generate new token (classic) → check `repo` scope

---

## PART 2 — Create DigitalOcean Droplet

### 👤 Step 4 — Create a Droplet
1. Log into DigitalOcean: https://cloud.digitalocean.com
2. Click **Create → Droplets**
3. Choose:
   - **Region:** New York or closest to you
   - **OS:** Ubuntu 22.04 LTS (x64)
   - **Size:** Basic → Regular → **$12/mo (2 GB / 1 CPU)**
   - **Authentication:** SSH Key (preferred) or Password
     - If using Password: pick a strong one and save it
4. Click **Create Droplet**
5. **Copy the Droplet IP address** (looks like `134.209.xx.xx`)

---

## PART 3 — Point veklom.dev to your Droplet

### 👤 Step 5 — Add DNS records
Go to wherever veklom.dev is registered (Namecheap, GoDaddy, Cloudflare, etc.)
Add these 2 DNS records:

| Type | Name | Value | TTL |
|------|------|-------|-----|
| A | @ | YOUR_DROPLET_IP | 300 |
| A | www | YOUR_DROPLET_IP | 300 |

> DNS can take up to 30 min to propagate. Move on while you wait.

---

## PART 4 — Set Up the Server (run once)

### 👤 Step 6 — SSH into your Droplet
Open a terminal and run:
```bash
ssh root@YOUR_DROPLET_IP
```
(If you used a password, enter it when prompted)

### 👤 Step 7 — Run the deploy script
```bash
curl -fsSL https://raw.githubusercontent.com/reprewindai/goonvault/main/deploy-veklom.sh -o deploy.sh
bash deploy.sh https://github.com/reprewindai/goonvault.git
```
> This installs Docker, clones your repo, and sets up the firewall.
> It will STOP and ask you to fill in the .env file. That's Step 8.

---

## PART 5 — Fill in Your Secrets

### 👤 Step 8 — Edit the .env file on the server
```bash
nano /opt/goonvault/.env
```

Fill in every line that says `CHANGE_ME`. Here's what each one needs:

| Variable | What to put |
|----------|-------------|
| `SECRET_KEY` | Run: `openssl rand -hex 32` — paste the output |
| `AI_CITIZENSHIP_SECRET` | Run: `openssl rand -hex 32` again — paste different output |
| `POSTGRES_PASSWORD` | Any strong password, e.g. `Vault#2026xQ9!` |
| `REDIS_PASSWORD` | Any strong password, e.g. `Redis#Vault77!` |
| `DATABASE_URL` | Replace `CHANGE_ME_strong_db_password` with your POSTGRES_PASSWORD |
| `REDIS_URL` | Replace `CHANGE_ME_strong_redis_password` with your REDIS_PASSWORD |
| `CELERY_BROKER_URL` | Same as REDIS_URL |
| `CELERY_RESULT_BACKEND` | Same as REDIS_URL |
| `STRIPE_SECRET_KEY` | Your live Stripe secret key (starts with `sk_live_`) |
| `STRIPE_PUBLISHABLE_KEY` | Your live Stripe publishable key (starts with `pk_live_`) |
| `STRIPE_WEBHOOK_SECRET` | Get from Step 9 below |

**To save and exit nano:** press `Ctrl+X` → `Y` → `Enter`

### 👤 Step 9 — Get Stripe Webhook Secret
1. Go to: https://dashboard.stripe.com/webhooks
2. Click **Add endpoint**
3. Endpoint URL: `https://veklom.dev/api/v1/stripe/webhook`
4. Events to send: select `checkout.session.completed`, `customer.subscription.updated`, `customer.subscription.deleted`
5. Click **Add endpoint**
6. Copy the **Signing secret** (starts with `whsec_`)
7. Paste it as `STRIPE_WEBHOOK_SECRET` in your .env

---

## PART 6 — Launch

### 👤 Step 10 — Start the platform
```bash
bash /opt/goonvault/deploy-veklom.sh https://github.com/reprewindai/goonvault.git
```
> This time it will detect the filled .env and launch everything.

### 👤 Step 11 — Verify it's live
```bash
# Check containers are running
docker compose -f /opt/goonvault/docker-compose.veklom.yml ps

# Check health
curl https://veklom.dev/health
```
Should return: `{"status":"ok","version":"..."}`

Then open your browser: **https://veklom.dev** ← your site is live!

---

## PART 7 — Admin Access

### 👤 Step 12 — Create your admin account
Run on the server:
```bash
docker exec -it goonvault-api python -c "
from db.session import SessionLocal
from db.models.user import User
from core.security.password import hash_password
db = SessionLocal()
u = User(email='YOUR_EMAIL@gmail.com', hashed_password=hash_password('YOUR_PASSWORD'), is_superuser=True, is_active=True)
db.add(u); db.commit()
print('Admin created!')
"
```
Replace `YOUR_EMAIL@gmail.com` and `YOUR_PASSWORD` with what you want.

### Admin dashboard URL
```
https://veklom.dev/admin/research
```
Login with the email/password you just created. That's it.

---

## Quick reference — useful server commands

```bash
# View live logs
docker compose -f /opt/goonvault/docker-compose.veklom.yml logs -f api

# Restart everything
docker compose -f /opt/goonvault/docker-compose.veklom.yml restart

# Pull new code + redeploy
cd /opt/goonvault && git pull && docker compose -f docker-compose.veklom.yml up -d --build

# Stop everything
docker compose -f /opt/goonvault/docker-compose.veklom.yml down
```

---

## What you get at veklom.dev

| URL | Page |
|-----|------|
| `veklom.dev` | GoonVault landing + pricing |
| `veklom.dev/browse` | Browse by niche with inline player |
| `veklom.dev/creators` | Creator application |
| `veklom.dev/admin/research` | Admin research dashboard (login required) |
| `veklom.dev/legal/terms` | Terms of Service |
| `veklom.dev/legal/privacy` | Privacy Policy |
| `veklom.dev/legal/2257` | §2257 compliance |
| `veklom.dev/api/v1/docs` | API documentation |
