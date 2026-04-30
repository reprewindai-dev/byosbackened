# BYOS AI Router — Definitive Pricing Model
> Inspired by IOMETE's open-core sovereign data lakehouse model.
> Last updated: April 2026

---

## The Core Philosophy

**Charge for the control plane license. Not for inference.**

Charging per token or per API call puts you in direct price comparison with OpenAI, Anthropic, and every other SaaS AI vendor — and you lose that fight. Instead, charge a flat annual license fee for the **routing, governance, cost intelligence, and security layer** that sits on top of any model, any vendor, any cloud.

This is exactly how IOMETE monetizes: they don't charge per query. They charge for the right to run the software that manages queries — sovereign, self-hosted, in the customer's own environment.

Your value proposition is identical, one layer up the stack:
> "You already pay for your AI APIs. We make that spend sovereign, auditable, cost-intelligent, and vendor-agnostic."

---

## The Four Layers — Priced Separately

| Layer | What It Is | Who Pays | Model |
|---|---|---|---|
| **Vendors** | AI providers listing models in the marketplace | Vendors | Free to list · Rev-share on routed volume |
| **Marketplace** | Model discovery, comparison, routing layer | Platform | % of routed spend or premium placement |
| **Workspace** | Each customer's sovereign isolated environment | Teams/Enterprise | Included in backend license |
| **Backend License** | The control plane (`byosbackened`) | Teams/Enterprise | Annual flat license fee |

---

## Backend License Tiers

### Free — Permanent, No Expiry
> For individual developers, researchers, and open-source builders.

- 1 workspace
- Up to 100K requests/month
- 3 vendor connections max
- Community support (Discord/GitHub Issues)
- No audit logs
- No SSO or RBAC
- No compliance exports
- Self-hosted only
- **License cost: $0 forever**

**Purpose:** Developer acquisition, GitHub stars, word-of-mouth. These users never pay directly — they bring in the enterprise deals.

> ⚠️ Gate: No work email required. Personal GitHub login fine.

---

### Team — $12,000/year flat
> For engineering teams evaluating or running production AI workloads.

- Unlimited workspaces
- Unlimited requests
- All vendor connections
- Audit logs + query history
- RBAC (role-based access control)
- Cost intelligence dashboard
- Budget controls + kill switch
- Silver support (5 tickets/month, 1hr Sev1 SLA)
- Onboarding: scoped separately
- **14-day full-feature trial (work email required)**

> ⚠️ Gate: Work email or one-question qualification form:
> *"How many AI API calls does your team make per month?"*
> This filters personal accounts and qualifies intent.

---

### Business — $25,000–$50,000/year flat
> For companies with compliance, privacy, or multi-vendor requirements.

- Everything in Team
- SSO (SAML/OIDC)
- GDPR/HIPAA-ready compliance exports
- Multi-vendor failover routing
- Content safety + data masking
- Privacy audit trail
- Locker security (BYOS credential isolation)
- Token wallet management
- Gold support (unlimited tickets, 30min Sev1 SLA, upgrade-to-urgent)
- Onboarding: scoped separately
- **14-day full-feature trial (qualified leads only)**

> ⚠️ Gate: Sales qualification call or demo before trial access.
> Target: Mid-market companies, 50–500 employees, $2M+ AI API spend/year.

---

### Enterprise — $75,000–$150,000+/year (custom)
> For mission-critical AI infrastructure at petabyte-adjacent scale.

- Everything in Business
- Multi-region routing
- Hybrid deployment (on-prem + cloud mix)
- Dedicated forward-deployed engineer (FDE) time
- Custom SLAs
- White-glove vendor onboarding
- Custom compliance configurations
- Platinum support (dedicated TSE, Slack/email, 24x7 Sev1+2)
- **Minimum commitment: $75,000/year**
- **No self-serve trial — demo + scoping call required**

> ⚠️ Target: Healthcare, finance, defence, regulated industries.
> These are companies who already self-host their data (IOMETE customers) and need sovereign AI on top.

---

## The 14-Day Trial — Who Gets It and Why

The 14-day trial is **for the backend license only** — not the marketplace, not vendor listings.

| Tier | Gets Trial? | Gate |
|---|---|---|
| Free | ❌ Permanent free tier instead | None |
| Team | ✅ 14 days, full features | Work email |
| Business | ✅ 14 days, full features | Sales qualification |
| Enterprise | ❌ Demo + scoping call instead | Direct sales |

**Why time-limited for Team/Business, not everyone:**

Individual devs on a countdown clock hit a wall and churn without buying. But a team evaluating with full features in 14 days will either:
1. See the value and convert immediately, or
2. Tell you exactly what's missing — worth more than 1,000 free signups.

**Trial mechanics:**
- License key issued at signup with 14-day TTL
- After expiry: control plane stops accepting new routes (data stays in their environment)
- The integration cost of ripping it out after 14 days of use is higher than the license — this is your close mechanism

---

## Vendor & Marketplace Monetization

### Vendor Side (Supply)
- **Always free to list** — you need supply-side density first
- **Rev-share on routed volume**: 2–5% of the API spend routed through your platform to their models
- **Premium placement**: $500–$2,000/month for featured listing in the marketplace

### Marketplace Side (Demand)
- Browsing and discovery: always free, no account required
- Routing through the marketplace without self-hosting: usage-based (% of spend)
- Self-hosting customers pay the backend license, not marketplace fees

---

## Support Tiers (Sold Separately, On Top of License)

| Plan | Included With | Upgradeable To |
|---|---|---|
| Community | Free tier | — |
| Silver | Team | Purchasable add-on |
| Gold | Business | Purchasable add-on |
| Platinum | Enterprise | Included |

Professional services (onboarding, migration, custom integrations) are always scoped separately — this is your FDE revenue layer and where passive income becomes active income only when you choose it.

---

## Revenue Model Summary

### Passive Income Path (Target)
| Source | Annual Value Per Customer | Notes |
|---|---|---|
| Team licenses | $12K | Low-touch, self-serve after trial |
| Business licenses | $25–50K | Mid-touch, some onboarding |
| Enterprise licenses | $75–150K | High-touch, but few customers needed |
| Vendor rev-share | Variable | Scales with marketplace GMV |

**5 Team customers = $60K ARR**
**3 Business customers = $75–150K ARR**
**1 Enterprise customer = $75–150K ARR**

You do not need hundreds of customers. You need 5–15 serious ones.

### Active Income Path (Optional)
| Source | Value | When to Offer |
|---|---|---|
| FDE time | $150–250/hr | Only when you choose to engage |
| Onboarding packages | $5–25K flat | Scoped per customer |
| Custom compliance builds | $10–50K | Enterprise only |

---

## Why Not Per-Token Pricing

Per-token pricing creates three problems for this product:

1. **Comparison trap** — Customers immediately compare you to OpenAI/Anthropic/Groq prices and ask "why pay you on top of paying them?"
2. **Misaligned incentives** — You profit when they spend more, which contradicts the cost intelligence value prop
3. **Unpredictable revenue** — Flat annual licenses create predictable ARR; token fees create volatile MRR

The IOMETE proof: they built a $250K/year minimum contract business on flat licensing, not query fees. Your control plane is worth more than a per-call fee implies.

---

## Competitive Positioning

| Competitor | Model | Your Advantage |
|---|---|---|
| OpenAI API | Per-token, vendor-locked | Sovereign, multi-vendor, no lock-in |
| Databricks AI | Cloud SaaS, expensive at scale | Self-hosted, 2-5x cheaper at volume |
| LiteLLM | Open source, no commercial layer | Managed control plane, compliance, support |
| IOMETE | Data layer sovereignty | AI layer sovereignty (complementary, not competing) |

---

## The Customer Funnel

```
Marketplace (free, no account)
        ↓
Workspace signup (free tier)
        ↓
Hit free tier limits → 14-day Team trial
        ↓
Integrated + dependent → Team license ($12K)
        ↓
Compliance/SSO needed → Business ($25–50K)
        ↓
Mission-critical + regulated → Enterprise ($75K+)
```

The marketplace is the top of funnel.
The backend trial is the close mechanism.
The license expiry is the urgency.

---

*This document supersedes `PRICING_STRATEGY.md` and `PRICING_TRUTH.md`.*
*Internal use only — not for public distribution.*
