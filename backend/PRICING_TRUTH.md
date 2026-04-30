# Pricing Truth - Single Source of Reference

Purpose: prevent the public page, the backend, and the Stripe dashboard from drifting apart. Every price visible to a customer in any system must match this table.

## Authoritative Prices

| Tier | Public Display Name | Internal Key | Monthly | Yearly (10x monthly) | Currency |
|---|---|---|---:|---:|---|
| Team | Team | `starter` | $12,000.00 | $120,000.00 | USD |
| Business | Business | `pro` | $35,000.00 | $350,000.00 | USD |
| Enterprise | Enterprise | `enterprise` | Custom | Custom | USD |
| Strategic Transfer (Private) | Not publicly listed | n/a - manual | $1,000,000.00 | n/a | USD |

Yearly = monthly x 10. Two months free. That matches the public page disclaimer.

## Where these numbers must appear identically

| Location | File / Surface | Must show |
|---|---|---|
| Public landing page | `landing/pricing.html` | $12,000 / $35,000 / Custom |
| SoftwareApplication JSON-LD | `landing/pricing.html` (head) | Same three recurring prices |
| FAQPage JSON-LD | `landing/pricing.html` (head) | Pricing FAQ answer references same numbers |
| Backend plan catalog | `apps/api/routers/subscriptions.py` -> `PLANS` | `1_200_000` / `3_500_000` cents (Enterprise custom) |
| API endpoint | `GET /subscriptions/plans` | Returns the public PLANS dict |
| Stripe Dashboard products | `Veklom Team` / `Veklom Business` / `Veklom Enterprise` | Same monthly + yearly prices |
| Sales decks / proposals | Any PDF or email | Same numbers, no exceptions |
| Cold-email pitch templates | `PILOT_PRICING_INTERNAL.md` | Standard rate matches; pilot rate is separate, see that doc |

## What's intentionally not here

- Pilot/charter discount rates ($1,500 / $4,000 / $9,500). These are private and live only in `PILOT_PRICING_INTERNAL.md`. They are never on the public page, in code, or in JSON-LD.
- Strategic transfer value is internal-only and never shown on public pages. It is negotiated privately outside Stripe Checkout.

## Stripe Dashboard setup checklist

Before any customer is asked to pay, the Stripe dashboard should contain:

- [ ] Product `Veklom Team` with two recurring prices: $12,000/month + $120,000/year
- [ ] Product `Veklom Business` with two recurring prices: $35,000/month + $350,000/year
- [ ] Product `Veklom Enterprise` - custom pricing, sales-assisted only
- [ ] All products tagged with metadata `{ "tier": "starter|pro|enterprise" }` for reconciliation
- [ ] `STRIPE_SECRET_KEY` set in production environment (`core/config.py` reads `stripe_secret_key`)
- [ ] `STRIPE_WEBHOOK_SECRET` set in production environment
- [ ] Webhook endpoint `https://api.veklom.com/api/v1/subscriptions/webhook` registered in Stripe dashboard, listening for:
  - `checkout.session.completed`
  - `customer.subscription.created`
  - `customer.subscription.updated`
  - `customer.subscription.deleted`
- [ ] Test mode verified end-to-end with a Stripe test card (4242 4242 4242 4242) on the Team tier first
- [ ] Production mode verified with one real $12,000 transaction (refund immediately, smoke test only)

The current backend code uses `price_data` inline in Checkout sessions, so pre-creating prices in Stripe is not strictly required for the flow to work, but it is strongly recommended for accounting reconciliation. Pre-created prices give finance a stable mapping when reading Stripe exports.

## Reality check on enterprise sales

For $7,500-$45,000/mo deals, most regulated buyers will not swipe a card. The realistic flow is:

1. Cold outreach -> written exchange -> NDA
2. Technical evaluation -> architecture review
3. MSA negotiation (procurement)
4. Stripe Invoice with NET 30 ACH/wire instructions or a one-time Stripe Payment Link sent by email
5. Customer pays via wire, treasury reconciles in 2-5 business days
6. Subscription marked `active` manually in admin UI; webhook handler is the fallback

Self-serve `/subscriptions/checkout` is fine for the smaller pilot customers paying by card. Enterprise customers will not use it.

## When prices change

If pricing ever changes, update in this exact order, atomically, in one PR:

1. This document (`PRICING_TRUTH.md`)
2. `apps/api/routers/subscriptions.py` -> `PLANS` dict
3. `landing/pricing.html` and any price summaries in `backend/landing/`
4. Stripe Dashboard (create new prices, archive old, update webhook config)
5. Sales decks and cold-email templates
6. Existing customers - honor old rates per their signed MSAs; new prices apply only to new contracts

Never push the page change without the backend change. Never push the backend change without the Stripe change. A 1-hour drift between these is acceptable for a deploy window. A 1-day drift is a billing-disclosure incident.
