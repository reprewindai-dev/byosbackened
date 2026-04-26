# Deploy Veklom to veklom.com — Click-by-Click

**Goal:** Have `https://veklom.com` live with working email forwarding for `hello@veklom.com` and `procurement@veklom.com`, in about **20 minutes**, **for $0** beyond what you already paid for the domain.

**Architecture you'll end up with:**

```
                 You own veklom.com
                          │
                          ▼
          Cloudflare (one dashboard does everything)
          ├─ DNS              (free, instant updates)
          ├─ Email Routing     (free, hello@ → your Gmail)
          ├─ Pages (hosting)   (free, auto SSL, global CDN)
          └─ Analytics         (free, privacy-respecting)
```

You don't need GoDaddy hosting, you don't need Google Workspace, you don't need a separate web host. Cloudflare does it all in one place, free.

---

## Step 0 — Make sure you can do this

You need:
- [ ] You own `veklom.com` (you said you do)
- [ ] Login access to whatever registrar you bought it from (GoDaddy, Namecheap, Squarespace, etc.)
- [ ] A real Gmail or other email address you actually check (this is where buyer emails will land)
- [ ] Roughly 20 minutes

If you're missing any of these, stop and fix them first.

---

## Step 1 — Make a Cloudflare account (3 min)

1. Go to **https://dash.cloudflare.com/sign-up**
2. Email + password. Verify the email. Done.

That's it. No credit card. No "free trial." Just a free account.

---

## Step 2 — Add veklom.com to Cloudflare (3 min)

1. In the Cloudflare dashboard, click **"Add a site"** (top right or in the sidebar)
2. Type `veklom.com`. Click continue.
3. Pick the **Free** plan ($0/month). Continue.
4. Cloudflare will scan your existing DNS records — wait ~30 seconds.
5. You'll see a list of any existing records. If you don't have any (typical for an unused domain), it'll be empty. Click **Continue**.
6. **You'll see two nameservers** that look like:
   ```
   amber.ns.cloudflare.com
   carlos.ns.cloudflare.com
   ```
   (The names are randomized per account — these are just examples. Yours will be different.)

   **Keep this tab open.** You need these nameservers in the next step.

---

## Step 3 — Change nameservers at your registrar (5 min)

This is the only step that varies by registrar. Find your registrar below and follow that subsection. The pattern is always: log in → find DNS / Nameserver settings → replace the existing nameservers with the two Cloudflare ones from Step 2.

### If you bought it at GoDaddy

1. Log into **godaddy.com**
2. Click your name (top right) → **My Products**
3. Find `veklom.com` in the list → click **DNS** next to it
4. Scroll to **Nameservers** section → click **Change**
5. Pick **"I'll use my own nameservers"**
6. Paste the two Cloudflare nameservers (one per line). Save.

### If you bought it at Namecheap

1. Log into **namecheap.com**
2. Sidebar → **Domain List**
3. Find `veklom.com` → click **Manage**
4. Find **Nameservers** dropdown → change to **"Custom DNS"**
5. Paste the two Cloudflare nameservers. Click the green ✓.

### If you bought it at Squarespace Domains (formerly Google Domains)

1. Log into **account.squarespace.com**
2. Find your domain → click into it
3. Sidebar → **DNS Settings**
4. Scroll to **Nameservers** section → **Use custom nameservers**
5. Add the two Cloudflare nameservers. Save.

### If you bought it at Porkbun

1. Log into **porkbun.com**
2. Click your domain in the dashboard
3. Find **Authoritative Nameservers** → click the edit (pencil) icon
4. Replace with the two Cloudflare nameservers. Save.

### If you bought it somewhere else

Search your registrar's docs for "change nameservers." Every registrar has this feature; the menu path is always 3-5 clicks deep. The two Cloudflare nameservers go where the existing nameservers were.

---

## Step 4 — Wait for nameserver propagation (1 min – 24 hr, usually 5 min)

1. Go back to your Cloudflare tab (the one from Step 2)
2. Click **"Done, check nameservers"** (or the equivalent button)
3. Cloudflare will check every few minutes. Most of the time, propagation is done in under 10 minutes.
4. You'll get an email from Cloudflare titled something like *"Cloudflare is now protecting veklom.com"* when it's done.

**While you wait, do Step 5 (it doesn't depend on this).**

---

## Step 5 — Enable Cloudflare Email Routing (3 min)

This is what makes `hello@veklom.com` and `procurement@veklom.com` actually work. Buyers email those addresses, Cloudflare forwards to your Gmail.

1. In the Cloudflare dashboard, click your domain (`veklom.com`)
2. Sidebar → **Email** → **Email Routing**
3. Click **Enable Email Routing**. Cloudflare adds the required MX and TXT records to your DNS automatically. Click **Add records and enable**.
4. Now you're on the Email Routing dashboard. Click the **Routes** tab.
5. Click **Create address**:
   - **Custom address:** `hello`
   - **Action:** Send to an email
   - **Destination:** your real Gmail address (e.g. `yourname@gmail.com`)
   - Click **Save**
6. Click **Create address** again:
   - **Custom address:** `procurement`
   - **Action:** Send to an email
   - **Destination:** same Gmail
   - Click **Save**
7. Cloudflare sends a verification email to your Gmail. **Open Gmail, click the verification link.** You only need to verify once per destination.

**Test it:**
From any other email account, send a test email to `hello@veklom.com`. It should arrive in your Gmail within a minute. If it does, email is working.

**Optional but recommended:** in Gmail → Settings → Accounts → "Send mail as" → add `hello@veklom.com` so you can REPLY from that address as well as receive. Cloudflare Email Routing is receive-only by default; outbound from `@veklom.com` goes through Gmail's "Send as" feature using a Gmail app password. Takes 5 extra minutes if you want it.

---

## Step 6 — Deploy the website to Cloudflare Pages (5 min, free)

The site is already built. The folder `landing/` contains `index.html`, `logo.svg`, `favicon.svg`, `robots.txt`, `sitemap.xml`. That's everything Cloudflare Pages needs.

### Path A (fastest — direct upload, deploys in 60 seconds)

1. In the Cloudflare dashboard sidebar → **Workers & Pages** → click **Create application** → tab **Pages** → **Upload assets**
2. **Project name:** `veklom` (this becomes `veklom.pages.dev` until you attach the custom domain)
3. **Production branch:** leave default
4. **Drag the entire `landing/` folder** onto the upload area (or click and pick all files inside it)
5. Click **Deploy site**
6. Wait ~30 seconds. You'll get a URL like `https://veklom.pages.dev`.
7. Open it in a new tab. **The site should load.** You're now hosted, free, with auto SSL, on a global CDN.

### Path B (better long-term — Git auto-deploy)

If you want every code change to automatically redeploy:

1. Push the `landing/` folder to a GitHub repo (private or public, doesn't matter)
2. In Cloudflare → **Workers & Pages** → **Create application** → **Pages** → **Connect to Git**
3. Authorize GitHub. Pick the repo.
4. Build settings:
   - **Build command:** *(leave empty)*
   - **Build output directory:** `landing` (if the repo root has the folder) or `/` (if you pushed only the contents of `landing/`)
5. Save. Cloudflare deploys automatically on every push to main.

**Pick Path A if you want to be live in 60 seconds and don't want to learn Git workflow yet. Switch to Path B later.**

---

## Step 7 — Attach veklom.com to the Pages site (3 min)

The site is now live at `veklom.pages.dev`. To put it on `veklom.com`:

1. In the Pages project (Cloudflare dashboard → Workers & Pages → click your `veklom` project)
2. Tab **Custom domains** → **Set up a custom domain**
3. Type `veklom.com` → click **Continue**
4. Cloudflare detects the domain is already on its DNS (because of Step 2-4) → click **Activate domain**
5. Cloudflare adds a CNAME record automatically and provisions an SSL certificate. Wait ~2 minutes.
6. Repeat for `www.veklom.com`:
   - Click **Set up a custom domain**
   - Type `www.veklom.com` → activate

That's it. **`https://veklom.com` is now live, with valid SSL, served from a global CDN, for $0/month.**

---

## Step 8 — Verify everything works (5 min)

Click through this checklist. Everything should pass.

| Check | How to verify | Expected |
|---|---|---|
| Domain resolves | Open `https://veklom.com` in browser | Page loads |
| SSL valid | Browser shows padlock, no warnings | ✅ valid cert |
| `www` redirects | Open `https://www.veklom.com` | Same page |
| Email forwarding | Send test email to `hello@veklom.com` from any other account | Lands in your Gmail within 1 min |
| Procurement email | Send to `procurement@veklom.com` | Same |
| Sitemap | Open `https://veklom.com/sitemap.xml` | XML loads |
| Robots | Open `https://veklom.com/robots.txt` | Text loads |
| OG preview | Paste `https://veklom.com` into Twitter/LinkedIn compose | Title + description appear (image will be missing, see optional step below) |
| Mobile | Open on phone | Page is readable, all sections render |

If everything passes, **you're live**.

---

## Step 9 — Submit to Google Search Console (5 min, optional but recommended)

Without this, Google takes 1–3 weeks to find you. With it, indexing starts within 24 hours.

1. Go to **https://search.google.com/search-console**
2. Add property → **Domain** option → enter `veklom.com`
3. Google gives you a TXT record to add to verify ownership
4. Cloudflare dashboard → veklom.com → DNS → Records → Add record:
   - Type: `TXT`
   - Name: `@` (or leave blank)
   - Content: paste the value Google gave you
   - Save
5. Back in Google Search Console → click **Verify**. Should pass instantly.
6. Once verified, click **Sitemaps** in the left sidebar → submit `sitemap.xml`
7. Done. Google will start crawling within 24 hours.

Repeat for **Bing Webmaster Tools** if you want Bing/DuckDuckGo coverage too. Same flow, takes 5 more minutes.

---

## Optional: Add the OG social preview image (10 min)

The page references `https://veklom.com/og-image.png` for social shares. Right now that file doesn't exist, so Twitter/LinkedIn previews show no image (text only).

To fix:
1. Make a 1200×630 PNG with the Veklom seal/logo on a dark background and the tagline "Sovereign AI Operations" — Canva, Figma, or any image editor works
2. Save as `og-image.png` in the `landing/` folder
3. Re-upload to Cloudflare Pages (Path A) or git push (Path B)
4. Test with the LinkedIn Post Inspector: https://www.linkedin.com/post-inspector/
5. Test with the Twitter Card Validator: https://cards-dev.twitter.com/validator

This is purely cosmetic. The page works without it. But it dramatically increases click-through on shared links, so do it before you start cold-emailing.

---

## What it looks like when you're done

- `https://veklom.com` — your live site, served from Cloudflare's global CDN
- `hello@veklom.com` and `procurement@veklom.com` — real, forwarding to your Gmail
- Free SSL, auto-renewing
- Free DNS with instant updates
- Free analytics (Cloudflare → Analytics tab) showing where visitors come from
- Free DDoS protection (Cloudflare default)
- Cost so far: **$0** (plus the ~$10 you already paid for the domain)

---

## Things you can ignore for now

- **CDN configuration** — Cloudflare's defaults are fine
- **Page Rules / Workers** — not needed for a static site
- **Cloudflare Access / Zero Trust** — overkill for a public marketing site
- **Workspace email** — Cloudflare Email Routing covers receive; Gmail "Send as" covers send

---

## When something breaks

Most likely problem: **email forwarding stops working.** Cause: 99% of the time, someone deleted the MX records that Cloudflare auto-added. Fix: Cloudflare → veklom.com → Email Routing → Settings → "Reset records" button.

Second most likely: **`https://veklom.com` shows a Cloudflare error page.** Cause: the Pages custom domain wasn't fully provisioned. Fix: wait 10 minutes; if still broken, remove and re-add the custom domain.

Third most likely: **certificate warning in browser.** Cause: SSL hasn't provisioned yet (rare; usually instant). Fix: wait 15 minutes. If still failing, email Cloudflare support — it's free.

---

**Total active time: ~20 minutes. Total cost: $0. After this you have a real, branded, professional vendor presence at `veklom.com` that any bank or hospital procurement officer can email and any Google search can find.**
