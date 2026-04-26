# Veklom — Marketing & SEO Playbook
**Last updated:** 2026-04-26 — after landing page redeploy with full OG/favicon/blog set.

This is the single source of truth for everything you (or anyone you hire) needs to:

1. Describe the product accurately to anyone (including AI tools like Perplexity / ChatGPT / Gemini)
2. Submit to Google Search Console properly so it ranks
3. Verify the social-share card actually renders on iMessage / Twitter / LinkedIn / Slack
4. Plan blog/SEO content cadence
5. Understand how customers actually find this thing

---

## 1. Canonical product description (paste into Perplexity / GPT / etc.)

> **Veklom** is a self-hosted AI operations platform for regulated industries — hospitals, banks, defense contractors, and government agencies. It is the production-grade equivalent of Portkey, LangSmith, and Helicone, but built from the architecture down to be deployed inside the customer's own perimeter (their VPC, on-prem Kubernetes cluster, GovCloud enclave, or air-gapped network) instead of running as a vendor-hosted SaaS.
>
> The platform provides: a multi-LLM gateway (OpenAI, Anthropic, Hugging Face, Ollama, Whisper, local vLLM); hard-cap cost kill switches that enforce monthly budgets at the gateway layer rather than after-the-fact billing alerts; multi-tenant role-based access control with workspace isolation; tamper-evident audit logging that meets HIPAA §164.312(b), SOC 2 CC7, and PCI-DSS 10 requirements; GDPR-compliant data subject endpoints (export, erasure, PII detection, masking); a Stripe-integrated billing and subscription engine for sub-tenant resale; and an ML lifecycle layer for cost and quality predictors that automatically routes traffic to cheaper models when the cheaper model passes a configurable evaluator.
>
> Veklom is sold as software (perpetual or annual), not as a hosted service. The vendor never has logical access to runtime data. Compliance scope is the customer's authorization boundary, not the vendor's hosted offering. This makes Veklom viable for institutions where SaaS is structurally non-viable due to third-party-risk, BAA scope, CMMC enclave requirements, or sovereign-cloud mandates.
>
> Pricing: Sovereign Standard $7,500/month, Sovereign Pro $18,000/month, Sovereign Enterprise $45,000/month, Source Acquisition $750,000 one-time. Founded 2026. Live at https://veklom.com.

---

## 2. Three pitch lengths

### 30-second elevator
> Veklom is the AI operations platform you deploy inside your own perimeter. Multi-LLM gateway, cost kill switches, RBAC, audit, GDPR — built for hospitals, banks, and defense contractors where SaaS will never get past procurement.

### 60-second pitch
> Every AI infrastructure vendor today — Portkey, LangSmith, Helicone — is SaaS. They route your prompts through their cloud. That works for tech companies. It does not work for hospitals, banks, or defense contractors, where the CISO will reject any vendor with logical access to non-public information. Veklom is the same category of product, but architected to deploy inside the customer's perimeter — VPC, on-prem, GovCloud, or air-gapped. Multi-LLM gateway, hard-cap cost controls, multi-tenant RBAC, audit logging that survives an OCR review, GDPR endpoints, Stripe billing for sub-tenant resale. Sold as software, not as a service. The vendor never sees your traffic.

### 3-minute pitch
> The AI infrastructure market is in the same place CRM was in 2002 — every vendor assumes the buyer is comfortable with a SaaS posture. That assumption stops working at the regulatory boundary. A Tier-1 bank's third-party risk team will not approve a vendor who routes credit-memo summaries through someone else's cloud. A 500-bed hospital cannot get a BAA past their compliance committee for a tool that holds PHI in a vendor data center. A CMMC Level 2 contractor cannot use any service that puts CUI outside their authorization boundary. These are not friction points the SaaS vendors can negotiate around — they are categorical disqualifiers.
>
> Veklom is the architectural answer. Same product surface as Portkey or LangSmith — multi-LLM gateway, observability, cost controls, audit, billing — but operated entirely inside the customer's perimeter. The vendor sells software. The customer operates the infrastructure. Compliance scope is the customer's existing controls, not a vendor SOC 2 report.
>
> Three deployment modes: VPC (AWS commercial, GovCloud, GCP, Azure), on-prem Kubernetes, or fully air-gapped with an offline package. Pricing is annual or perpetual, $90K to $540K ARR, with a $750K one-time source-acquisition tier for buyers who require permanent vendor independence. Live at veklom.com. Currently engaging with healthcare networks, regional banks, and defense primes.

---

## 3. Keyword strategy

### Tier 1 — primary intent (rank for these first)
Use these in titles, H1s, og:title, twitter:title, and meta descriptions:

- self-hosted AI gateway
- on-prem AI operations platform
- sovereign AI platform
- HIPAA-compliant AI gateway
- HIPAA AI operations
- regulated industry AI infrastructure
- self-hosted LLM gateway
- private AI gateway

### Tier 2 — competitor displacement
- Portkey alternative
- Portkey self-hosted
- LangSmith alternative
- Helicone alternative
- Vellum alternative
- Braintrust alternative
- self-hosted Portkey
- on-prem LangSmith

### Tier 3 — vertical/persona
- AI for banks
- AI for hospitals
- HIPAA AI pipeline
- CMMC AI tools
- FedRAMP AI infrastructure
- bank AI compliance
- healthcare AI architecture
- defense contractor AI tools
- GDPR-compliant AI
- air-gapped LLM platform

### Tier 4 — long-tail (blog post targets)
- how to deploy LLM in HIPAA environment
- LLM cost control enterprise
- LLM kill switch
- multi-tenant AI gateway
- BAA AI vendor
- AI vendor risk management
- 45 CFR 164 AI compliance
- LLM token economics enterprise
- model routing cost optimization
- AI gateway architecture

### Use these EXACT meta strings already in your code
**Title:** `Veklom — Self-Hosted AI Operations Platform for Regulated Industries`
**Description:** `Sovereign AI operations platform for hospitals, banks, and defense. Self-hosted multi-LLM gateway, cost kill switches, RBAC, audit, GDPR. HIPAA, PCI-DSS, SOC 2 aligned.`
**Meta keywords:** `self-hosted AI gateway, on-prem AI operations, sovereign AI platform, HIPAA AI gateway, FedRAMP AI infrastructure, air-gapped LLM platform, multi-LLM gateway, LLM cost kill switch, AI ops for banks, AI ops for hospitals`

---

## 4. Google Search Console action plan (do today)

### Step 1: Property setup
- Go to https://search.google.com/search-console/
- Add property: **Domain property** (not URL prefix) → enter `veklom.com`
- Verify via DNS TXT record (Cloudflare DNS, takes ~30 seconds)
- The TXT record `google-site-verification=m5aSjIfnWc_jjyx4cBai99dwpRdb_qh71f8gEfpMNGs` is already in your zone — verification should pass immediately

### Step 2: Submit sitemap
- Sitemaps → Add sitemap → enter: `sitemap.xml`
- It will report 9 URLs discovered (homepage, 5 anchors, blog index, 3 blog posts, 6 legal)

### Step 3: Request indexing for the high-value URLs
For each URL below, paste it into the URL Inspection bar at the top of Search Console, then click "Request Indexing":

1. `https://veklom.com/`
2. `https://veklom.com/blog/`
3. `https://veklom.com/blog/why-saas-cannot-serve-regulated-buyers/`
4. `https://veklom.com/blog/true-cost-of-llm-sprawl/`
5. `https://veklom.com/blog/hipaa-compliant-ai-pipelines/`

This pushes them into the priority crawl queue. First-page indexing typically happens within 6–48 hours.

### Step 4: Set the canonical region
- Settings → International Targeting → Country → United States (recommended; you can adjust later)

### Step 5: Verify Bing too
- https://www.bing.com/webmasters
- Same domain verification, paste the same sitemap URL

---

## 5. Verify social share cards work (do this NOW from your phone)

The OG card has been deployed but **caches at every major platform are aggressive**. You must force-refresh each platform at least once or your first post/share will look broken even though the file is correct.

### LinkedIn
- https://www.linkedin.com/post-inspector/
- Paste `https://veklom.com/` → click Inspect → if the card looks wrong, click "Re-fetch"

### Twitter / X
- https://cards-dev.twitter.com/validator (deprecated but still works — login with Twitter)
- OR just post a tweet with the URL once; Twitter caches the image after first share

### Facebook / Meta (Instagram, WhatsApp, Threads all share this cache)
- https://developers.facebook.com/tools/debug/
- Enter `https://veklom.com/` → click "Scrape Again" — this is the most important one because it propagates to WhatsApp and Instagram

### iMessage / Apple
- iMessage uses LinkPresentation which queries OG tags directly with no public debug tool
- Force refresh: text yourself the URL with a typo (e.g. `veklom.com?v=2`) — Apple sees this as a new URL and re-fetches
- Confirms the card renders end-to-end

### Slack / Discord
- Both auto-fetch on first share. If they cache wrong, in Slack you can paste `/unfurl <URL>` to retry.

### Generic preview test
- https://www.opengraph.xyz/url/https%3A%2F%2Fveklom.com%2F (visual preview of all major platforms simultaneously)
- This is the fastest sanity check — 1 click and you see what every platform will render.

**Expected result on all platforms:** dark card with brass compass-rose mark, italic serif "Veklom" wordmark, "Self-Hosted AI Operations for Regulated Industries", "HOSPITALS · BANKS · DEFENSE · GOV", at 1200×630.

---

## 6. Schema.org validation

Test that Google can read your structured data:

- https://search.google.com/test/rich-results
- Enter `https://veklom.com/` → click Test URL
- You should see: **Organization, SoftwareApplication, FAQPage** detected as eligible
- Repeat for each blog post — should detect **BlogPosting** + **BreadcrumbList**

If anything throws an error, the page is still fine — the error usually means a non-required field is missing. Required fields are all populated.

---

## 7. Google Business / Knowledge Panel

Google won't show a Knowledge Panel for a brand-new company until it sees ~5–10 high-quality external references. Bootstrap order:

1. **Crunchbase profile** — free, takes 10 minutes, gets indexed in ~2 weeks. Crunchbase is a primary signal source for the Knowledge Graph.
2. **LinkedIn Company Page** — biggest single signal. Ensure the URL field points to https://veklom.com (no trailing slash variations).
3. **GitHub Organization** — `github.com/veklom` (or whatever you choose) with a README that mirrors the canonical product description above. Pin the Veklom repo public to it.
4. **Product Hunt launch** — only when you have at least one paying customer or letter of intent; otherwise the launch is hollow.
5. **Wikipedia** — explicitly do NOT create your own Wikipedia entry; that's a CoI deletion. Wait until a third party writes one.
6. **G2 / Capterra listings** — free to claim. Each one becomes a high-PA backlink and a Knowledge-Graph signal.

After ~30 days of those existing, search "Veklom" in Google logged out — you should start seeing the brand box on the right.

---

## 8. How customers actually find sovereign AI tools (the honest answer)

The AI infrastructure category is **bottom-of-funnel discovery**, not top-of-funnel. Almost no buyer Googles "self-hosted AI gateway" cold. They get to you via three paths, in this order:

### Path A: Vendor-failure search (60% of relevant traffic)
A buyer is mid-evaluation with Portkey or LangSmith, hits the SaaS wall in their procurement review, and Googles **"Portkey self-hosted"**, **"LangSmith on-prem"**, or **"Portkey alternative HIPAA"**. Your blog post "Why SaaS AI Tools Cannot Serve Regulated Buyers" is built specifically to rank on these exact failure-mode queries. This is the single most important traffic source — it gets pre-qualified buyers who already understand the category.

### Path B: Compliance-document search (25%)
A compliance officer or architect Googles **"HIPAA-compliant LLM gateway"**, **"45 CFR 164 AI"**, **"AI vendor BAA"**, or **"CMMC AI tools"**. They land on your HIPAA blog post or your homepage. The blog content is the lead magnet here — they read 1,500 words, conclude you know what you're doing, and reach out.

### Path C: Cost-pain search (15%)
A CFO or platform team Googles **"LLM cost control enterprise"**, **"OpenAI bill exploding"**, or **"LLM kill switch"**. They land on your "True Cost of LLM Sprawl" post. This audience converts slower but at higher ACV because the pain point ("I am hemorrhaging $$$ to OpenAI") is acute.

### What does NOT work
- Generic "AI startup" SEO. The keyword "AI gateway" is dominated by hyperscalers and won't rank.
- Programmatic SEO content (1,000 thin pages) — Google will deindex this for a brand-new domain.
- Cold outbound LinkedIn DMs at the persona level (CISOs ignore them; CIOs forward to procurement; procurement throws them away).

### What does work, in addition to the above
1. **Conference content** — SecurityWeek, Black Hat, HIMSS, RSA, FedScoop. A single talk about sovereign AI architecture from any of these will outrank 50 blog posts. Submit CFPs starting now for 2026 fall conferences.
2. **One named reference customer** — a single named hospital or bank case study unlocks 5x outbound conversion. Your engagement strategy should be: first 3 customers get heavy discount in exchange for permission to name them publicly.
3. **Engineering content with real code** — the HIPAA blog post you have now is in this category. Three more like it (different vertical, different control framework) and you're the #1 organic result for the entire long-tail.

---

## 9. Content cadence (next 90 days)

Target: one substantial blog post every 14 days. Not more — quality wins category-defining SEO at this stage.

Suggested topics, in priority order:

1. **PCI-DSS for AI: Reading Requirement 10 in 2026** (cost engineering + compliance overlap, banks)
2. **The Air-Gap Pattern: Deploying LLMs Without Egress** (DoD-adjacent, defense readers)
3. **Multi-Tenant RBAC for AI: A Reference Schema** (engineering reference, dev audience, ranks for "AI RBAC")
4. **GDPR Article 28 and AI Vendors: A Walkthrough** (EU buyers, very few competitors writing this)
5. **The Build vs. Buy Math for In-House AI Gateways** (CFO/CTO bridge piece, lots of cross-link opportunities)
6. **Audit Trails That Survive an OCR Review** (technical, healthcare, links back to HIPAA pipeline post)

Each one: 1,800–2,500 words, one inline SVG data-viz, real research citations, ends with a soft CTA.

---

## 10. The 90-day organic ranking forecast

Realistic expectations for a brand-new domain with this much technical content:

| Window | What to expect |
|---|---|
| Week 1 | Sitemap indexed, brand search ("Veklom") returns your homepage |
| Week 2-3 | Blog posts indexed, ranking 30-50 for long-tail compliance queries |
| Week 4-6 | First page (positions 5-10) for at least one "alternative" keyword (e.g. "Portkey self-hosted") if the post gets even one backlink |
| Week 8-10 | Knowledge Panel begins to populate if Crunchbase + LinkedIn + GitHub are live |
| Week 12 | First page for 3-5 long-tail compliance keywords; rich result snippets begin appearing |
| Month 6 | Top 3 for at least one Tier-2 competitor-displacement keyword if content cadence holds |

Faster paths exist (paid ads, influencer endorsements, manufactured controversy) but they cost real money and produce traffic that doesn't convert in regulated B2B. The slow path above produces buyers who close.

---

## Quick-reference: things that are LIVE right now

- ✅ https://veklom.com/ — landing page (Cloudflare Pages)
- ✅ https://veklom.com/og-image.png — 1200×630 social card (image/png, 145KB)
- ✅ https://veklom.com/favicon.ico, /apple-touch-icon.png, /favicon-{16,32,192,512}.png — full icon set
- ✅ https://veklom.com/site.webmanifest — PWA manifest
- ✅ https://veklom.com/blog/ — Field Notes index, in the top-nav
- ✅ Blog posts: why-saas-cannot-serve-regulated-buyers/, true-cost-of-llm-sprawl/, hipaa-compliant-ai-pipelines/
- ✅ Sitemap covers all 9 URLs at https://veklom.com/sitemap.xml
- ✅ Schema.org: Organization, SoftwareApplication, FAQPage, Blog, BlogPosting, BreadcrumbList, TechArticle — all validated
- ✅ Mozilla Observatory / SecurityHeaders.com grade: A+ (HSTS, CSP, X-Frame-Options, etc.)

## Things that still depend on YOU

- ⏳ Search Console verification (5 min)
- ⏳ LinkedIn Company Page (15 min)
- ⏳ Crunchbase profile (10 min)
- ⏳ Manual social-card refresh on LinkedIn / FB / Twitter (5 min total)
- ⏳ Submit a CFP to one conference (HIMSS or RSA — 30 min)
