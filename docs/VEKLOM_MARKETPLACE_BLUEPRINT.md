# Veklom Marketplace Blueprint

## Source of Truth

This blueprint reflects the live marketplace at `veklom.com` and `veklom.com/vendor`.
If the live site changes, this blueprint must be revised to match.

## Product Definition

Veklom is a sovereign AI infrastructure marketplace.

Core positioning:

- regulated AI infrastructure
- token-metered execution
- self-hosted or air-gapped deployment
- spend control with hard caps and kill switches
- audit-grade controls
- buyer trust through evidence, not hype

## Current Public Surface

### Main Site

- Marketplace
- Pricing
- Vendors
- Dashboard
- Sign In
- Get Access

### Public Hero

Run AI jobs without losing control of spend or data.

### Trust Signals

- Sovereign Verified
- SOC 2
- HIPAA
- GDPR
- 99.9% SLA
- 14-day free trial

## Commercial Model

### Buyer Plans

The public pricing page sells subscription access plus monthly credits.

Plans:

- Free
- Starter
- Pro
- Sovereign
- Enterprise

### Token Packs

Customers can buy additional credits at any time.

Packs:

- Starter Pack
- Growth Pack
- Team Pack
- Enterprise Pack

### Consumption Rules

- Credits are the primary metering unit.
- API requests return `402 Payment Required` when credits are exhausted.
- Monthly included credits expire at the end of the billing period.
- Purchased token-pack credits remain until consumed.

## Buyer Experience

The marketplace is designed for buyers who want evidence before purchase.

The public site shows:

- live simulation
- scenario-based product demo
- regulated-industry use cases
- pricing with explicit limits
- self-host and air-gap claims
- vendor and marketplace entry points

## Live Simulation Model

The simulation is part of the public sales surface.

Supported scenarios:

- Memorial Health System
- First National Bank
- Apex AI Agency

Simulation states:

- Incoming Request
- PII Detection
- Auto-Redaction
- Token-Metered Execution
- Governed Result

Business purpose:

- prove control before purchase
- demonstrate compliance behavior
- make spend governance visible
- show audit trail generation

## Vendor Model

The vendor page is the marketplace intake path.

Public vendor tiers:

- Verified Listing
- Sovereign Verified

### Verified Listing

- price: $199/mo
- better marketplace placement
- full vendor profile page
- request-access form for buyers
- basic listing analytics
- reviewed within 5 business days
- sovereign badge path
- compliance review path

### Sovereign Verified

- price: $1,500 setup + $500/mo
- sovereign badge and premium placement
- compliance documentation review
- security controls checklist
- audit/logging explanation verification
- full vendor analytics dashboard
- marketplace sales support
- priority listing review in 48h

### Transaction Fee Model

When transactions are enabled:

- vendor receives 70-80%
- Veklom platform fee is 20-30%

## Sovereign Graduation Standard

Essential tools can graduate into Sovereign Verified if they provide:

1. SBOM or dependency disclosure
2. deployment documentation
3. data-flow explanation
4. security controls
5. audit/logging explanation
6. support terms

## Vendor Submission Flow

The public listing form supports:

- company or organization name
- product name
- category
- application tier
- GitHub repository URL
- deployment model
- documentation URL
- pricing model
- contact email
- compliance claims
- product description

The live flow also supports GitHub connection so the marketplace can:

- link the repository
- pull the README
- detect capabilities
- pre-fill listing fields
- show star counts on the marketplace card

## Revenue Architecture

Revenue streams currently visible on the public site:

- subscriptions
- annual plans
- token packs
- vendor listing fees
- sovereign verification fees
- future transaction fees

## Product Constraints

The marketplace is not positioned as generic hosting.

Current public constraints:

- self-hosted in VPC or air-gapped
- no data calls home
- governance at runtime
- spend caps and kill switches
- evidence-first sales motion
- regulated buyer focus

## Site Copy Rules

Use this language consistently:

- sovereign infrastructure
- token-metered
- controlled spend
- governed AI
- audit-grade execution
- compliance reports
- self-hosted
- air-gapped
- evidence over rapport

Do not revert to the old internal product naming unless the public site changes.

## Update Rule

This blueprint is a living snapshot of the live product.

Any time the public site changes:

1. update the site copy first
2. update pricing and vendor terms
3. update this blueprint
4. update any related docs or sales assets

## Deployment Notes

The docs should stay aligned with:

- the public homepage
- the pricing page
- the vendor page
- the live demo behavior
- the current plan and token-pack structure
