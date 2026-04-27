# Veklom Marketplace Blueprint — Built Around BYOSBackend

## 0. Purpose

This blueprint defines how to turn **BYOSBackend** into the commercial engine behind **Veklom Marketplace**.

The goal is not to build a generic hosting company. The goal is to sell access to Veklom’s existing backend capabilities — tokens, cost controls, routing, auditability, execution governance, marketplace listings, and premium control features — through a premium marketplace experience that matches Veklom’s positioning.

**Core principle:**

> Veklom does not start as a place where strangers upload huge backends. Veklom starts as the marketplace and control layer powered by BYOSBackend, with Veklom’s own backend as the first premium product.

---

## 1. Product Thesis

Regulated and AI-heavy teams do not only need “AI tools.” They need:

- cost control
- policy control
- token control
- endpoint access control
- audit trails
- safe execution
- buyer-friendly procurement
- usage visibility
- optional sovereign/self-hosted paths later

BYOSBackend already contains many backend capabilities. The marketplace must package those capabilities into clear buyer-facing products and plans.

The marketplace should answer:

> “Why does this tier cost money?”

The answer is:

> “Because this tier unlocks specific BYOSBackend capabilities that save money, reduce runaway AI costs, govern execution, and make usage easier to audit.”

---

## 2. What Veklom Is Selling First

The first premium listing is **Veklom BYOSBackend**.

Positioning:

> **The backend control layer for sovereign AI operations.**

Buyer-facing line:

> **Run AI and backend workflows without losing control of your data, tokens, or costs.**

Veklom is not just selling a dashboard. Veklom is selling governed access to backend capabilities.

---

## 3. Hosting Strategy: What We Host and What We Do Not Host

### 3.1 Current infra reality

The current production server should be treated as a **control node**, not a general hosting platform.

It should run:

- the Veklom marketplace app
- user accounts/auth
- listing database
- subscription/payment state
- token/credit ledger
- BYOSBackend gateway/API control layer
- usage event ingestion
- admin approvals
- lightweight execution only when explicitly approved

It should not run arbitrary customer infrastructure.

### 3.2 What is allowed at launch

Allowed:

- Veklom’s own backend
- marketplace/control plane
- token/credit accounting
- API gateway calls
- short-lived execution jobs
- small wrappers/connectors
- approved lightweight jobs
- download/self-host listings
- buyer requests for access

### 3.3 What is not allowed at launch

Not allowed:

- arbitrary full SaaS app hosting
- customer databases
- vendor databases
- long-running third-party services
- big custom backends
- GPU-heavy workloads on the main server
- training jobs
- uncontrolled container hosting

### 3.4 Later expansion

If demand is proven, add:

- dedicated worker nodes
- queue-based execution
- GPU worker pools
- customer-hosted agent/controller
- private enterprise deployments
- marketplace-managed customer VPC installs

---

## 4. Marketplace Structure

The marketplace has two sides:

### 4.1 Sovereign Marketplace

For regulated or serious buyers.

Requirements:

- no outbound telemetry or clearly documented data flow
- self-hosted/customer-controlled option where applicable
- compliance artifacts
- audit/logging support
- clear pricing
- approved by Veklom
- higher trust positioning

This is the premium side.

### 4.2 Essential Marketplace

For useful tools that do not fully qualify as sovereign.

These may be:

- useful developer tools
- AI wrappers
- productivity tools
- internal tools
- vendor-hosted SaaS links
- tools with weaker compliance documentation

They still create value, but they do not get the premium sovereign badge until they meet the standard.

### 4.3 Graduation path

Essential tools can graduate to Sovereign after they provide:

- SBOM or dependency disclosure
- deployment documentation
- data-flow explanation
- security controls
- audit/logging explanation
- support terms
- pricing clarity

---

## 5. Listing Types

### 5.1 First-party Veklom listing

This is the main product.

Includes:

- BYOSBackend access
- subscription tiers
- token/credit usage
- cost-control features
- endpoint modules
- usage logs
- premium backend capabilities

Revenue: Veklom keeps 100%.

### 5.2 Vendor catalog listing

Vendor does not upload a giant backend to Veklom.

Vendor submits:

- product name
- product description
- category
- Sovereign or Essential application
- deployment model
- docs/support link
- compliance claims
- pricing proposal
- contact/support details

Buyer can:

- request access
- purchase through marketplace later
- download/self-host if allowed
- contact vendor through Veklom

Revenue: Veklom can take 20–30% on transactions once payments are enabled.

### 5.3 Lightweight Veklom-routed listing

Later, selected vendors can submit small functions/jobs that run through Veklom with strict limits.

Allowed examples:

- prompt transform
- document cleaner
- model routing helper
- small API wrapper
- connector call
- short queue job

Not allowed:

- persistent backend
- database
- long-running process
- heavy compute

---

## 6. BYOSBackend Capability Mapping

Because BYOSBackend has many endpoints, we must map endpoints into buyer-facing modules.

### 6.1 Core modules

#### Module A — Access & Identity

Backend capabilities likely include:

- auth
- API keys
- account/team control
- roles
- permissions

Marketplace value:

- secure access
- team governance
- enterprise readiness

Plan placement:

- Starter: single user/basic keys
- Pro: team access/API keys
- Sovereign: RBAC/policy controls
- Enterprise: custom org controls

#### Module B — Token Wallet / Credits

Backend capabilities:

- token balances
- credit purchases
- usage deductions
- transaction ledger
- plan allowances

Marketplace value:

- usage-based billing
- predictable spend
- no runaway invoices

Plan placement:

- Starter: small included credits
- Pro: bigger wallet + top-ups
- Sovereign: budgets by project/team
- Enterprise: custom token contracts

#### Module C — Cost Controls

Backend capabilities:

- budget caps
- usage limits
- per-user/per-project ceilings
- kill switches
- usage warnings

Marketplace value:

- saves customers money
- prevents AI bill shock
- beats Helicone-style soft alerts if Veklom enforces hard limits

Plan placement:

- Starter: basic monthly limit
- Pro: project limits + alerts
- Sovereign: hard caps + enforcement
- Enterprise: custom policy/budget rules

#### Module D — Routing & Model Control

Backend capabilities may include:

- route requests
- model/provider selection
- fallback logic
- cost-aware routing
- latency-aware routing

Marketplace value:

- lower model spend
- better reliability
- optimized provider choice

Plan placement:

- Starter: default routing
- Pro: cost-aware routing
- Sovereign: policy-aware routing
- Enterprise: custom routing rules

#### Module E — Execution Governance

Backend capabilities:

- execution endpoints
- job/run management
- instance controls
- request policies
- workflow execution

Marketplace value:

- controlled AI/backend workflows
- safe execution without becoming a hosting company

Plan placement:

- Starter: limited runs
- Pro: more runs + queue priority
- Sovereign: logged/policy-controlled execution
- Enterprise: private worker strategy

#### Module F — Audit & Logs

Backend capabilities:

- request logs
- run logs
- usage logs
- proof records
- exportable traces

Marketplace value:

- compliance evidence
- buyer trust
- audit readiness

Plan placement:

- Starter: basic logs
- Pro: extended logs
- Sovereign: audit exports/proof trails
- Enterprise: custom retention/export formats

#### Module G — Marketplace Listings

Backend capabilities:

- listing creation
- approval status
- vendor metadata
- categories
- tool profiles
- request access

Marketplace value:

- commercial catalog
- vendor onboarding
- premium discovery layer

Plan placement:

- Community/Essential vendor: free or low-cost listing
- Sovereign vendor: paid review/verification
- Enterprise partner: custom listing/support

---

## 7. Pricing Model

Pricing must reflect backend value, not random page access.

### 7.1 Buyer plans

#### Starter — $49–$99/month

Audience:

- solo builders
- small teams
- early agencies

Includes:

- account access
- limited BYOSBackend endpoints
- basic token wallet
- monthly included credits
- basic usage logs
- access to Essential marketplace

Limits:

- low monthly requests
- no hard enterprise controls
- no compliance exports

#### Pro — $199–$499/month

Audience:

- AI agencies
- teams running workflows
- SMBs using AI tools

Includes:

- more endpoint access
- higher credits allowance
- token top-ups
- cost-aware routing
- usage analytics
- project/team limits
- access to selected Sovereign listings

Value:

- saves money through routing and caps
- prevents runaway usage
- gives teams visibility

#### Sovereign — $1,000–$3,000/month

Audience:

- regulated teams
- healthcare
- finance
- public-sector pilots
- serious enterprise evaluation

Includes:

- premium BYOSBackend endpoints
- hard budget caps
- audit logs/export
- policy enforcement
- compliance evidence package
- higher support priority
- Sovereign marketplace access

Value:

- not just usage; auditability and control
- can justify price through avoided procurement/compliance cost

#### Enterprise — Custom

Audience:

- banks
- hospitals
- government
- defense
- large AI platforms/agencies

Includes:

- custom endpoint access
- private limits
- private deployment option later
- custom contract/MSA
- dedicated support
- custom compliance docs
- optional dedicated worker nodes

Value:

- full procurement support
- control and evidence
- custom architecture

### 7.2 Token/credit model

Subscriptions give access. Tokens meter usage.

Tokens should be consumed for:

- executions
- gateway calls
- model/API usage
- heavy runs
- future GPU runtime
- premium routing events
- vendor-routed calls later

Token rules:

- every usage event writes to ledger
- every account has balance
- hard caps stop execution when balance/budget is exceeded
- admins can view spend by tool/project/user

This is one of the biggest competitive advantages.

### 7.3 Vendor plans

#### Free listing

- Essential-only
- manual approval
- limited profile
- no compliance badge

#### Verified listing — $99–$299/month

- better placement
- vendor profile
- request-access form
- basic review

#### Sovereign verified — $500–$2,000 setup + monthly fee

- compliance review
- documentation checklist
- badge
- premium catalog placement
- marketplace sales support

#### Transaction fee

Once Stripe marketplace transactions are enabled:

- Veklom takes 20–30%
- vendor receives 70–80%

---

## 8. Competitive Win Map

### 8.1 Against Helicone

Helicone-style weakness:

- monitoring and alerts may not stop spend fast enough

Veklom angle:

- hard caps
- token wallet
- kill switches
- budget enforcement
- usage ledger

Sales line:

> Stop runaway AI spend before it becomes an invoice.

### 8.2 Against LangSmith

LangSmith-style weakness:

- cloud-first observability
- not ideal for air-gapped/regulated deployment

Veklom angle:

- backend control layer
- audit exports
- policy-based usage
- later self-host/customer-controlled path

Sales line:

> Observability is not enough. Regulated teams need controlled execution.

### 8.3 Against Portkey

Portkey-style weakness:

- gateway/control may still depend on external SaaS architecture depending on deployment

Veklom angle:

- sovereign positioning
- zero/controlled outbound design
- backend access tiers
- cost-control + audit together

Sales line:

> AI routing without sovereignty is still vendor risk.

### 8.4 Against generic SaaS AI vendors

Weakness:

- procurement drag
- uncontrolled data flow
- external dependency
- unclear usage costs

Veklom angle:

- marketplace + backend control
- token accounting
- vendor/product review
- one control layer

Sales line:

> Buy and run AI tools without losing control of spend, data, or execution.

---

## 9. Marketplace Pages Required

### 9.1 Home

Hero:

> AI and backend tools that do not run away with your data or your budget.

Sub:

> Veklom Marketplace is powered by BYOSBackend — a control layer for AI usage, cost limits, endpoint access, and sovereign-ready execution.

CTA:

- Start with Veklom
- Explore Marketplace
- Submit Tool

### 9.2 Veklom BYOSBackend product page

Sections:

- What it is
- Why it saves money
- Token wallet
- Cost controls
- Routing/model control
- Audit logs
- Endpoint modules
- Pricing
- Use cases
- CTA: Start subscription / request access

### 9.3 Pricing

Must show:

- Starter
- Pro
- Sovereign
- Enterprise
- Token top-ups
- vendor listing plans

### 9.4 Marketplace catalog

Filters:

- Sovereign
- Essential
- AI infrastructure
- cost control
- audit/compliance
- developer tools
- internal ops

Each listing card:

- name
- tier
- deployment model
- compliance status
- pricing model
- CTA

### 9.5 Vendor submission

Fields:

- company/product
- category
- Sovereign or Essential application
- deployment model
- docs link
- pricing
- compliance claims
- support contact
- file/docs upload later

### 9.6 Buyer dashboard

Shows:

- active plan
- token balance
- usage by endpoint/tool
- budget caps
- invoices
- API keys
- purchased listings

### 9.7 Admin dashboard

Shows:

- users
- plans
- listings pending approval
- token transactions
- endpoint usage
- flags/violations
- revenue

---

## 10. Backend Implementation Blueprint

### 10.1 Core tables

Required tables:

- users
- organizations
- memberships
- plans
- subscriptions
- token_wallets
- token_transactions
- usage_events
- endpoint_catalog
- endpoint_entitlements
- marketplace_listings
- listing_reviews
- vendor_profiles
- api_keys
- invoices/payments
- audit_logs

### 10.2 Endpoint catalog

Every BYOSBackend endpoint should be registered with:

- endpoint path
- method
- internal name
- module
- required plan
- token cost
- rate limit
- logging level
- sovereign eligibility
- public/private/admin classification

This turns 135+ endpoints into a product system.

### 10.3 Entitlement check

Every protected endpoint should enforce:

1. user authenticated
2. org active
3. subscription active or free tier allowed
4. endpoint is included in plan
5. token balance sufficient if tokenized
6. budget cap not exceeded
7. usage event logged
8. audit event stored if required

### 10.4 Token flow

When user calls tokenized endpoint:

1. estimate token/credit cost
2. check wallet balance
3. check budget cap
4. execute request
5. calculate final usage
6. deduct credits
7. write token transaction
8. write usage event
9. return response with remaining balance

### 10.5 Stripe flow

Subscriptions:

- Starter price ID
- Pro price ID
- Sovereign price ID
- Vendor listing price ID

One-time/top-up:

- token pack price IDs
- verification fee price ID

Webhooks:

- checkout.session.completed
- customer.subscription.created
- customer.subscription.updated
- customer.subscription.deleted
- invoice.paid
- invoice.payment_failed
- payment_intent.succeeded

Webhook updates:

- subscription status
- plan entitlements
- token top-up balance
- invoice/payment records

---

## 11. Security Rules

### 11.1 Public repo safety

If this repo remains public:

- no proprietary backend logic should be exposed beyond what is already public
- no secrets
- no API keys
- no Stripe keys
- no database URLs
- no provider tokens
- no private endpoint docs that reveal attack paths

Recommended:

- make backend repo private
- keep public marketing/docs separate

### 11.2 Runtime safety

- rate limit all API keys
- protect admin endpoints
- log all paid endpoint usage
- add budget kill switches
- do not allow arbitrary code execution initially
- isolate any future execution workers

### 11.3 Vendor safety

- vendors cannot upload arbitrary backend services
- vendors submit listings only at launch
- any runnable tool requires manual approval
- all execution must be sandboxed later

---

## 12. Build Plan for Windsurf

### Phase 1 — Inventory BYOSBackend

Task:

- scan backend routes
- extract all endpoints
- generate `endpoint_catalog.json`
- classify by module, plan, token cost, and risk

Output:

- endpoint inventory
- module map
- first pricing map

### Phase 2 — Marketplace shell inside Veklom aesthetic

Task:

- build marketplace pages using premium dark/gold Veklom aesthetic
- add home, catalog, Veklom product, pricing, vendor submit, dashboard

Output:

- production UI connected to backend routes where available

### Phase 3 — Billing foundation

Task:

- add Stripe checkout
- add subscription plans
- add token top-up checkout
- add webhook handling

Output:

- subscriptions and token wallet working

### Phase 4 — Endpoint entitlement middleware

Task:

- add middleware around BYOSBackend endpoints
- enforce plan access
- enforce tokens
- log usage

Output:

- paid backend access tied to plans

### Phase 5 — Admin and vendor review

Task:

- vendor submissions
- listing approval
- Sovereign/Essential classification
- admin dashboard

Output:

- real marketplace operating system

### Phase 6 — Launch

Task:

- Veklom BYOSBackend as first premium listing
- Essential/Sovereign catalog live
- Stripe live keys
- production server env configured
- DNS connected

Output:

- marketplace can accept buyers and vendors

---

## 13. Final Positioning

Use this everywhere:

> **Veklom is the marketplace for AI and backend tools that need cost control, usage governance, and sovereign-ready deployment.**

Short version:

> **Control your AI spend. Control your backend access. Control your deployment.**

Most important line:

> **The product is not hosting. The product is controlled backend access.**

---

## 14. Immediate Windsurf Prompt

Paste this into Windsurf:

```
We are building Veklom Marketplace around the existing BYOSBackend codebase.

Do not build a generic hosting platform.
Do not allow arbitrary third-party backend uploads.

First, inspect the backend and generate a complete endpoint inventory. Classify every endpoint by module, plan eligibility, token cost, and risk level.

Then build the marketplace around the actual backend capabilities:
- subscriptions for access
- token/credit wallet for usage
- hard budget caps
- usage event ledger
- endpoint entitlement middleware
- Veklom BYOSBackend as the first premium listing
- vendor submissions as catalog listings only at launch
- two marketplace tiers: Sovereign and Essential

Use a premium Veklom aesthetic: dark background, gold accents, clean enterprise layout, high-trust compliance language.

Required pages:
- home
- marketplace catalog
- Veklom BYOSBackend product page
- pricing
- vendor submission
- buyer dashboard
- admin dashboard

Required backend work:
- endpoint_catalog table/json
- plan entitlements
- token wallets
- token transactions
- usage events
- Stripe subscriptions
- Stripe token top-ups
- webhook handler
- protected endpoint middleware

The main product is controlled access to BYOSBackend, not third-party hosting.
```
