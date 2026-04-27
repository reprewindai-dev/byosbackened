# Wednesday Agent Execution Plan — Veklom Marketplace Powered by VCB

## Status

This is the review-first plan for the Wednesday build agent.

Public naming is locked:

- **Veklom Marketplace**
- **Powered by VCB**
- **VCB = Veklom Control Backend**

The repo name is internal only and must not appear in customer-facing copy.

---

## 1. Core Product Truth

Veklom Marketplace is not a generic hosting platform.

Veklom Marketplace sells controlled backend access, tokenized usage, budget enforcement, auditability, compliance workflows, and marketplace discovery powered by VCB.

The first premium product is VCB itself.

The marketplace has two sides:

1. **VCB first-party product** — Veklom keeps 100% revenue.
2. **Marketplace listings** — vendors submit catalog listings for review. They do not upload large backends or arbitrary services at launch.

---

## 2. Hard Launch Constraints

The Hetzner/headless server should be treated as a control node.

Allowed at launch:

- Veklom site/app
- VCB API/control layer
- user/auth/session logic
- Stripe subscription and credit checkout
- token wallet / credit ledger
- usage event logging
- marketplace listing database
- admin review
- lightweight approved jobs only

Not allowed at launch:

- arbitrary vendor backend hosting
- customer databases
- vendor databases
- uncontrolled containers
- GPU-heavy workloads
- training jobs
- full SaaS hosting for third parties
- long-running unbounded processes

---

## 3. Product Architecture

### 3.1 User-facing layers

- Landing page
- Pricing page
- VCB product page
- Marketplace catalog
- Vendor submission page
- Buyer dashboard
- Billing dashboard
- Usage dashboard
- Admin dashboard

### 3.2 Backend/commercial layers

- Auth/account/org
- Stripe subscriptions
- Stripe token packs
- VCB endpoint catalog
- Plan entitlements
- Token wallet
- Token transactions
- Usage events
- Budget caps
- Audit logs
- Admin approvals
- Marketplace listings

---

## 4. VCB Modules From Uploaded Route Files

The agent must inspect these modules and extract exact routes:

- `kill_switch.py`
- `locker_monitoring.py`
- `locker_security.py`
- `admin.py`
- `audit.py`
- `auth.py`
- `autonomous.py`
- `billing.py`
- `budget.py`
- `compliance.py`
- `content_safety.py`
- `cost.py`
- `exec_router.py`
- `explainability.py`
- `export.py`
- `extract.py`
- `health.py`
- `insights.py`
- `job.py`
- `search.py`
- `security_suite.py`
- `subscriptions.py`
- `suggestions.py`
- `transcribe.py`
- `upload.py`
- `metrics.py`
- `monitoring_suite.py`
- `plugins.py`
- `privacy.py`
- `routing.py`

The route map must be generated from actual decorators/routes, not guessed from filenames.

---

## 5. Pricing and Tier Logic

### Starter — $99/month

For builders and small teams testing controlled backend access.

Includes:

- account access
- login/session/profile
- limited API keys
- basic health/status
- limited execution
- basic token wallet
- limited cost prediction
- basic usage summary
- Essential marketplace access

Does not include:

- kill switch
- compliance reports
- audit verification
- advanced routing
- advanced security controls
- plugin execution
- enterprise admin controls

### Pro — $499/month

For AI teams and agencies trying to reduce waste.

Includes Starter plus:

- higher execution limits
- routing select/statistics
- cost prediction/history
- savings insights
- projected savings
- budget status/forecast
- billing breakdown
- performance metrics
- alerts summary
- text content scan
- job history
- search/usage analytics
- token top-ups

Positioning:

> Optimize usage before it becomes waste.

### Sovereign — $2,500/month

For regulated teams that need control and evidence.

Includes Pro plus:

- hard budget caps
- kill switch
- audit logs
- audit verification
- compliance checks/reports
- privacy workflows
- explainability
- detailed health
- threat stats
- security controls
- file scan
- content logs
- governed execution
- audit/compliance exports
- Sovereign marketplace access

Positioning:

> Govern execution before it becomes risk.

### Enterprise — Custom

For banks, hospitals, government, defense, large AI operators.

Includes Sovereign plus:

- custom endpoint access
- custom usage limits
- custom compliance package
- dedicated support
- workspace/user administration
- advanced security control operations
- custom routing rules
- training/custom optimization if appropriate
- private deployment path later
- dedicated worker/GPU strategy later
- MSA/procurement support

Positioning:

> Private control for serious AI operations.

---

## 6. Token / Credit Model

Subscriptions unlock access. Credits meter usage.

### Token packs

- $25 starter pack
- $100 growth pack
- $500 team pack
- $2,000 enterprise usage pack

### Token rules

- Every tokenized endpoint must write a usage event.
- Every debit must write a token transaction.
- No credit balance means no tokenized execution.
- Budget cap exceeded means endpoint is blocked before execution.
- Tokens alone do not unlock Sovereign or Enterprise features.
- High-risk controls require plan entitlement and, where relevant, credits.

### Credit classes

- Free metadata: health, public pricing, marketplace browse = 0 credits
- Low-cost control: auth/profile/basic status = 0–10 credits
- Standard API: search/suggestions/basic metrics/cost predict = 25–100 credits
- AI/model route: routing/exec/content scan/transcription = variable
- Heavy workflow: job/file scan/extract/upload processing = variable + minimum
- Compliance/audit: compliance report/audit verification/export = 250–2,500 credits
- Enterprise control: kill switch/admin/custom training = plan-gated, not public token-only

---

## 7. Endpoint Classification Rules

The agent must create:

- `docs/ENDPOINT_INVENTORY.md`
- `config/endpoint-catalog.draft.json`

For every endpoint:

- method
- path
- source file
- handler
- current middleware
- purpose
- module
- risk level
- suggested plan
- tokenized true/false
- suggested credit class
- audit required true/false
- notes

Suggested plan values:

- public
- starter
- pro
- sovereign
- enterprise
- internal

Risk values:

- public
- authenticated
- paid
- sensitive
- sovereign
- admin
- internal-only

Important: internal platform admin endpoints must never be exposed to normal buyers.

---

## 8. Module-to-Plan Starting Map

### Starter modules

- auth basic
- health basic
- limited exec
- basic API key
- basic cost predict
- basic usage summary
- marketplace browse

### Pro modules

- routing select/stats
- cost history
- budget forecast/status
- billing breakdown
- savings/projected savings
- monitoring metrics
- alerts summary
- content text scan
- suggestions
- search own usage/logs
- job history
- transcribe small/medium tokenized
- upload limited/tokenized

### Sovereign modules

- kill switch
- audit logs
- audit verify
- compliance checks/reports
- privacy checks/reports
- explainability
- detailed health
- security dashboard
- threat stats
- file scan
- content logs
- governed execution
- audit/compliance exports

### Enterprise modules

- custom routing rules
- custom endpoint access
- custom limits
- admin workspace/user operations
- advanced security control operations
- training/custom optimization
- private deployment pathway
- dedicated worker/GPU strategy later
- procurement/MSA support

### Internal-only

- global admin endpoints
- platform owner operations
- destructive controls not scoped to customer org
- secrets/config management
- unrestricted plugin execution

---

## 9. Middleware / Entitlement Pipeline

Do not delete or replace existing middleware blindly.

First create:

- `docs/MIDDLEWARE_AUDIT.md`

For every middleware file/function:

- file path
- purpose
- current behavior
- protected routes
- dependencies
- risk
- keep/modify/wrap recommendation

### Required request pipeline

```text
Request
  ↓
existing security middleware
  ↓
auth/API key middleware
  ↓
organization/account resolver
  ↓
endpoint catalog lookup
  ↓
plan entitlement check
  ↓
rate limit check
  ↓
budget cap check
  ↓
credit/token pre-check
  ↓
handler executes
  ↓
usage event writer
  ↓
credit/token deduction
  ↓
audit logger when required
Response
```

### Required middleware functions

- `require_auth`
- `resolve_account_or_org`
- `load_endpoint_policy`
- `require_plan_entitlement`
- `enforce_rate_limit`
- `enforce_budget_cap`
- `require_credit_balance`
- `write_usage_event`
- `deduct_credits`
- `write_audit_event`
- `require_admin`

---

## 10. Database / Persistence Requirements

The agent must review current DB structure first.

Required logical tables/models:

- users
- organizations/accounts
- memberships
- plans
- subscriptions
- token_wallets
- token_transactions
- usage_events
- budget_caps
- endpoint_catalog
- endpoint_entitlements
- api_keys
- marketplace_listings
- vendor_profiles
- listing_reviews
- audit_logs
- stripe_customers
- stripe_events
- invoices/payments

Do not create duplicate tables if equivalents already exist. Map to existing models where possible.

---

## 11. Stripe Design

### Subscription products

- Veklom Starter — $99/month
- Veklom Pro — $499/month
- Veklom Sovereign — $2,500/month
- Veklom Enterprise — manual/custom

### One-time products

- Token Pack $25
- Token Pack $100
- Token Pack $500
- Token Pack $2,000
- Sovereign vendor review fee if vendor workflow is enabled

### Required webhooks

- `checkout.session.completed`
- `customer.subscription.created`
- `customer.subscription.updated`
- `customer.subscription.deleted`
- `invoice.paid`
- `invoice.payment_failed`
- `payment_intent.succeeded`

Webhook behavior:

- update subscription status
- assign plan entitlements
- add monthly included credits
- add purchased token credits
- record invoices/payments
- store idempotent Stripe events

---

## 12. Marketplace Pages

### Landing page

Hero:

> Veklom Marketplace — Powered by VCB

Headline options:

- Control backend access before costs run away.
- Control AI spend before it runs.
- Backend control for AI teams that need predictable usage.

Core line:

> Veklom Marketplace is powered by VCB, the Veklom Control Backend for token metering, budget caps, execution routing, audit logs, cost prediction, compliance checks, and savings insights.

### VCB product page

Must show:

- token wallet
- hard caps
- routing/cost control
- audit/compliance
- security/privacy
- endpoint governance
- usage ledger
- pricing

### Pricing page

Must show:

- Starter
- Pro
- Sovereign
- Enterprise
- token packs
- vendor listing options later

### Marketplace catalog

Two sections:

- Sovereign Marketplace
- Essential Marketplace

VCB is first premium listing.

### Buyer dashboard

Must show:

- active plan
- token balance
- budget caps
- usage by endpoint/module
- invoices
- API keys
- purchased/listed tools

### Admin dashboard

Must show:

- pending listings
- users/orgs
- usage events
- token transactions
- endpoint catalog
- plans/entitlements
- revenue
- flagged security/audit events

---

## 13. Competitive Positioning

### Against Helicone

They show usage after it happens.

VCB predicts costs, tracks savings, enforces budgets, and can stop execution.

Line:

> Stop runaway AI spend before it becomes an invoice.

### Against LangSmith

They help debug and observe.

VCB controls routing, execution, spend, audit, privacy, and compliance.

Line:

> Logs are not control. VCB governs what can run.

### Against Portkey

They route AI requests.

VCB routes, explains, budgets, audits, scans, forecasts, and controls.

Line:

> Routing saves money. Control prevents damage.

### Against SaaS AI tools

They sell access and push vendor risk onto the buyer.

VCB sells governed access with token wallets, endpoint entitlements, compliance proof, and budget caps.

Line:

> Use AI tools without losing control of spend, data, or execution.

---

## 14. Hetzner Deployment Plan

### Recommended domains

- `veklom.com` — public marketplace / landing
- `www.veklom.com` — redirect to apex
- `api.veklom.com` — VCB API
- `console.veklom.com` — dashboard/admin when separated

### Server role

This Hetzner server is the production control node.

Recommended stack:

- Ubuntu
- Caddy or Nginx reverse proxy
- app process via systemd/PM2 depending on framework
- managed Postgres preferred if available
- Redis later for queue/rate limit if needed
- Stripe webhook route exposed over HTTPS
- daily backups
- log rotation
- firewall only required ports open

### Required env vars

```bash
APP_URL=https://veklom.com
API_BASE_URL=https://api.veklom.com
DATABASE_URL=
JWT_SECRET=
ADMIN_EMAIL=
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=
STRIPE_STARTER_PRICE_ID=
STRIPE_PRO_PRICE_ID=
STRIPE_SOVEREIGN_PRICE_ID=
STRIPE_TOKEN_PACK_25_PRICE_ID=
STRIPE_TOKEN_PACK_100_PRICE_ID=
STRIPE_TOKEN_PACK_500_PRICE_ID=
STRIPE_TOKEN_PACK_2000_PRICE_ID=
```

### Deployment sequence

1. Confirm repo is private.
2. Run endpoint inventory and middleware audit only.
3. Review generated docs with owner and external reviewer.
4. Approve endpoint tiers and pricing.
5. Implement endpoint catalog and entitlement middleware.
6. Implement token wallet and usage ledger.
7. Implement Stripe test mode.
8. Build marketplace/VCB/pricing/dashboard pages.
9. Run local tests.
10. Deploy staging or protected preview.
11. Configure Hetzner reverse proxy.
12. Configure env vars.
13. Test Stripe webhooks.
14. Run smoke tests.
15. Switch to live Stripe after owner approval.

---

## 15. Wednesday Agent Prompt — Final Review-First Version

```text
You are working in the Veklom backend repo.

Public naming:
- Veklom Marketplace
- Powered by VCB
- VCB = Veklom Control Backend
- Do not use the repo name publicly.

Important product truth:
- Veklom is not a generic hosting platform.
- VCB is the first premium product/listing.
- Subscriptions unlock endpoint access.
- Tokens/credits meter usage.
- Budget caps stop overruns.
- Sovereign/Enterprise unlock audit, compliance, privacy, security, kill switch, and governed execution.
- Vendors submit catalog listings only at launch. They do not upload large backends or arbitrary services.

DO NOT implement yet.
DO NOT refactor existing backend behavior.
DO NOT delete middleware.
DO NOT expose internal admin endpoints.
DO NOT add Stripe live keys.
DO NOT create production migrations without review.

First create review docs only:

1. docs/ENDPOINT_INVENTORY.md
2. docs/MIDDLEWARE_AUDIT.md
3. config/endpoint-catalog.draft.json
4. docs/PRICING_AND_ENTITLEMENT_DRAFT.md
5. docs/DEPLOYMENT_PLAN_HETZNER.md

Use the route modules already present:
kill_switch, locker_monitoring, locker_security, admin, audit, auth, autonomous, billing, budget, compliance, content_safety, cost, exec_router, explainability, export, extract, health, insights, job, search, security_suite, subscriptions, suggestions, transcribe, upload, metrics, monitoring_suite, plugins, privacy, routing.

For every endpoint, capture:
- method
- path
- source file
- handler
- current middleware
- purpose
- module
- risk level
- suggested plan: public/starter/pro/sovereign/enterprise/internal
- tokenized true/false
- suggested credit class
- audit required true/false
- notes

For every middleware, capture:
- file/function
- purpose
- what it protects
- whether it should stay unchanged
- whether commercial entitlement logic should wrap it
- risks

Pricing draft must use:
- Starter $99/mo
- Pro $499/mo
- Sovereign $2,500/mo
- Enterprise custom
- token packs: $25, $100, $500, $2,000

After generating docs, stop and wait for owner review.
```

---

## 16. Final Operator Rule

No agent should start implementation until the review docs exist and the owner approves them.

This protects the backend, preserves existing middleware, and turns VCB into a real commercial product instead of a guessed marketplace build.
