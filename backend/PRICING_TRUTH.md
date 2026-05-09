# Pricing Truth - Single Source of Reference

Purpose: prevent the public page, backend, Stripe dashboard, and agent instructions from drifting apart. Every customer-facing price must match this file.

## Authoritative Model

No subscriptions. No tokens. No surprise invoices.

Veklom uses a one-time activation fee plus a USD-denominated Operating Reserve. The reserve never expires. Billable governed events debit reserve units where 1,000 reserve units = $1.00.

## Activation And Reserve

| Tier | Public Display Name | Internal Key | Activation | Minimum Operating Reserve | Checkout |
|---|---|---|---:|---:|---|
| Free Evaluation | Evaluate | n/a | $0 | $0 | none |
| Founding | Founding Activation | `starter` | $395 | $150 | self-serve |
| Standard | Standard | `pro` | $795 | $300 | self-serve |
| Regulated | Regulated | `sovereign` | from $2,500 | $2,500 | sales-assisted |
| Enterprise | Enterprise | `enterprise` | private terms | private terms | sales-assisted |

Free Evaluation includes 15 governed Playground runs, 3 compare runs, 20 policy tests, 2 watermarked exports, BYOK provider testing, and marketplace browsing.

## Billable Event Ladder

| Event | Founding | Standard | Regulated |
|---|---:|---:|---:|
| Playground governed run | $0.25 | $0.40 | contact |
| Compare run | $0.75 | $1.20 | contact |
| Pipeline test | $0.25 | $0.40 | contact |
| Endpoint test / deployment verification | $0.50 | $0.80 | contact |
| UACP plan compile | $1.50 | $2.00 | contact |
| UACP governed execution | $3 | $4 | contact |
| UACP artifact generation | $5 | $7 | $10 |
| Signed Playground export | $3 | $4 | contact |
| BYOK Governance Calls (per 1,000) | $6 | $8 | $10 |
| Managed Governance Calls (per 1,000) | $12 | $16 | $20 |
| Signed Evidence Package | $99 | $149 | $199 |
| Auditor Bundle | $249 | $349 | $499 |

## Where These Numbers Must Appear Identically

| Location | File / Surface | Must show |
|---|---|---|
| Public pricing page | `landing/pricing.html` | Activation + reserve + event ladder |
| Backend plan catalog | `apps/api/routers/subscriptions.py` -> `PLANS` | activation cents and minimum reserve cents |
| AI billing route | `apps/api/routers/ai.py` | per-event reserve unit debits |
| Pipeline execution route | `apps/api/routers/pipelines.py` | pipeline test reserve debits |
| Deployment test route | `apps/api/routers/deployments.py` | endpoint test reserve debits |
| Wallet route | `apps/api/routers/token_wallet.py` | Operating Reserve packs |
| API endpoint | `GET /api/v1/subscriptions/plans` | Returns this public plan model |
| Stripe Dashboard | Products / Checkout | One-time activation payments and reserve funding |
| Sales decks / proposals | Any PDF or email | Same activation, reserve, and event prices |

## Stripe Dashboard Setup Checklist

- [ ] Product `Veklom Founding Activation` with one-time price $395.
- [ ] Product `Veklom Standard Activation` with one-time price $795.
- [ ] Product `Veklom Regulated Activation` handled by private quote or invoice.
- [ ] Products tagged with metadata `{ "tier": "starter|pro|sovereign|enterprise", "billing_model": "activation_plus_reserve" }`.
- [ ] `STRIPE_SECRET_KEY` set in production.
- [ ] `STRIPE_WEBHOOK_SECRET` set in production.
- [ ] Webhook endpoint `https://api.veklom.com/api/v1/subscriptions/webhook` registered in Stripe.
- [ ] Webhook listens for `checkout.session.completed`, `invoice.payment_failed`, `charge.dispute.created`, `charge.refunded`, and legacy subscription lifecycle events during migration.
- [ ] Test mode verified with a Stripe test card on Founding Activation first.

The backend creates inline Stripe Checkout prices, so pre-created Stripe prices are not required for the flow to work. Pre-created products are still recommended for accounting and reconciliation.

## Webhook Removal Risk

Checkout session polling can reconcile paid activation and reserve sessions if a browser returns to the app. Stripe webhooks are still required for asynchronous failures: payment failure, refund, dispute, cancellation, and license deactivation signals. Removing the webhook is an operational risk and must alert immediately.

## When Prices Change

Update in one PR:

1. This document.
2. `apps/api/routers/subscriptions.py`.
3. `apps/api/routers/ai.py`.
4. `apps/api/routers/token_wallet.py`.
5. Public pricing page and structured data.
6. Stripe Dashboard.
7. Sales decks and email templates.

Never push public pricing without backend pricing. Never push backend pricing without Stripe reconciliation coverage.
