# Veklom × Stripe — One-Page Go-Live Guide

**Designed for someone who finds Stripe confusing.** Each step is small. Read one, do one, then come back.

If you get stuck on any step, **screenshot the screen and paste the image in chat.** I'll tell you exactly what to click. No key info is in those screenshots — they're safe to share.

---

## ⚠️ First, the security thing

**NEVER paste a Stripe key into chat with me, with ChatGPT, into Slack, into Discord, or anywhere except a local file on your computer.**

Live Stripe keys are like the PIN to your bank card. They go in **one** place: a file called `backend/.env.stripe` on your computer. That file is gitignored — it never gets uploaded.

If you ever accidentally paste a key anywhere else: go to https://dashboard.stripe.com/apikeys and click **"Roll key"** within 1 minute. The key dies, you make a new one. No harm done if you act fast.

---

## The 5 things you do (everything else is automated)

### ① Activate your Stripe account (10 minutes, one-time, ONLY YOU CAN DO THIS)

US banking law (Bank Secrecy Act / KYC) requires the human account owner to enter their identity details personally. No software, AI, or person can do this for you.

1. Go to https://dashboard.stripe.com
2. Sign in with your email + password.
3. Look for an **orange banner at the top** that says "Activate payments" or "Complete your account." Click it.
4. Fill in the form:
   - **Country:** United States (or wherever you actually live)
   - **Business type:** "Individual / Sole proprietor" if you haven't incorporated yet. If you've made an LLC or corporation, pick "Company."
   - **Legal name + DOB**
   - **SSN** (last 4 digits in the US is enough most of the time)
   - **Home address**
   - **Business name:** "Veklom" (or whatever you want public-facing)
   - **Statement descriptor:** "VEKLOM" — this is what shows up on customer credit-card statements
   - **Bank account:** routing number + account number for whichever bank you want money deposited to
5. Upload a photo of your driver's license (use your phone camera).
6. Click **Submit**.

**Stripe will tell you "Account activated" within 5 minutes** for US accounts. You're done with this step.

---

### ② Turn on 2-Factor Authentication (2 minutes)

Stripe requires this for live mode anyway, and it protects your money.

1. Go to https://dashboard.stripe.com/settings/user
2. Click **"Two-step authentication"**
3. Use the **Authy** or **Google Authenticator** app on your phone (free).
4. Save the backup codes somewhere safe (like a password manager, or print them).

---

### ③ Make a Restricted Key with the right permissions (3 minutes)

We do **not** use the full secret key (`sk_live_...`). We use a **restricted key** (`rk_live_...`) that only has the permissions our setup script needs. If it ever leaks, the damage is limited.

1. Go to https://dashboard.stripe.com/apikeys
2. Click **"+ Create restricted key"** (right side of the page).
3. **Key name:** `veklom-setup-bot`
4. **Permissions** — set ONLY these to **Write**, leave everything else as **None**:
   - Products → **Write**
   - Prices → **Write**
   - Webhook Endpoints → **Write**
   - Customers → **Write**
   - Checkout Sessions → **Write**
   - Customer Portal → **Write**
5. Click **Create key**.
6. Stripe will show you the key once. **Copy it.** Starts with `rk_live_...`.
7. Also from https://dashboard.stripe.com/apikeys, **copy the Publishable key** (starts with `pk_live_...`).

---

### ④ Paste the keys into the local file (1 minute)

1. Open VS Code or Notepad.
2. Open this file (create it if it doesn't exist):
   ```
   c:\Users\antho\OneDrive\Desktop\.windsurf\byosbackened\backend\.env.stripe
   ```
3. Paste this template, replacing each placeholder with your real values:
   ```
   STRIPE_SECRET_KEY=rk_live_paste_the_restricted_key_here
   STRIPE_PUBLISHABLE_KEY=pk_live_paste_the_publishable_key_here
   STRIPE_WEBHOOK_SECRET=
   ```
   Leave `STRIPE_WEBHOOK_SECRET=` blank — the setup script generates it.
4. **Save. Close the file. Don't paste these in chat.**

---

### ⑤ Tell me "ready" and walk away

Type "ready" or "go" in chat. I will:

1. Run `python scripts/setup_stripe.py`
2. The script will create your 3 products, 6 prices, webhook endpoint, customer portal config — all programmatically.
3. The script will print the new **webhook signing secret** in the terminal. I'll paste it into your `.env.stripe` for you.
4. Run `python scripts/verify_stripe.py` to confirm everything is green.
5. Show you a checklist: ✅ products, ✅ prices match landing page, ✅ webhook listening, ✅ test checkout session works.

You sit back and watch.

---

## What the scripts do (transparency)

`scripts/setup_stripe.py` is **idempotent** — safe to run twice, won't create duplicates. It tags every object it creates with `metadata.veklom_id` so it can find and update them on re-run.

`scripts/verify_stripe.py` only **reads** Stripe. It doesn't modify anything. It just checks that what setup_stripe.py created is still correct, and that the prices in the codebase match the prices in Stripe.

Both scripts read your key from `.env.stripe` only. They never log it. They never echo it. They print Price IDs and Product IDs — those are safe to share publicly (they're like ISBN numbers, not secrets).

---

## After it's all green

You'll have:

- ✅ Live Stripe account, charges + payouts enabled
- ✅ 3 products + 6 prices, exactly matching the landing page
- ✅ Webhook endpoint listening at `https://api.veklom.com/api/v1/subscriptions/webhook`
- ✅ Customer portal so customers can self-cancel
- ✅ All wired into the backend code (price IDs in `stripe_setup_output.json`)

The first real customer who clicks "Subscribe" on the pricing page will:
1. Hit Stripe Checkout (hosted by Stripe — no card data touches your servers)
2. Pay $7,500 / $18,000 / $45,000
3. Trigger the webhook → backend creates a `Subscription` row → unlocks the tier
4. Money lands in your bank account in 2 business days (US default rolling payout)

---

## If something goes wrong

- **"charges_enabled = False"** → activation isn't done yet. Go back to Step ①.
- **"Authentication failed"** → restricted key permissions are wrong. Re-do Step ③.
- **"product MISSING"** → `setup_stripe.py` didn't run cleanly. Run it again — it's idempotent.
- **Anything else** → screenshot + paste in chat. I'll fix it.

---

_Last updated: 2026-04-26._
