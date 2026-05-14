# Veklom Operating Doctrine

This file is the product and engineering alignment document for production work.
It exists to keep Veklom's frontend, backend, marketplace, and agents consistent.

## Product Identity

Veklom is a sovereign AI control plane for governed execution.

It is not a generic chatbot, token wallet, demo shell, or model directory.
The product value is policy-before-provider routing, operating reserve control,
tenant-scoped execution, audit integrity, and exportable evidence.

## Runtime Routing

Default execution should use the primary sovereign runtime:

- Hetzner-hosted/headless local runtime
- Ollama/local model path where connected and policy-allowed
- Tenant-scoped model settings

Fallback and burst execution must only happen when one of these is true:

- The selected model/provider is explicitly a fallback/cloud provider.
- The primary runtime is unavailable and the scoped circuit breaker is open.
- Tenant policy allows the fallback path.
- A workload requires a provider-specific route such as AWS Bedrock.

Every governed run must record:

- Requested provider and model
- Actual provider and model
- Whether fallback fired
- Routing reason
- Latency
- Operating reserve impact
- Audit hash

UI must not label all fallback as "AWS burst." Use the actual provider when
known, or "Approved fallback" when the provider is not yet known.

## Commercial Language

Public and workspace UI should use:

- Governed runs
- Operating reserve
- Reserve impact
- Evidence packs
- Auditor bundles
- Activated workspace

Avoid visible commercial language built around:

- Usage credit tokens
- Generic token wallet
- Fake customer metrics
- Fake MRR/churn/customer data

Token counts can remain as technical telemetry when needed, but the customer
pricing and reserve model is based on governed execution events.

## Free Evaluation vs Activated Workspace

Free evaluation can show the governed execution flow and short-lived run
details. It must not provide compliance-grade exports.

Activated workspaces unlock:

- Durable retention
- Signed artifacts
- Evidence pack export
- Auditor bundles
- Bulk audit export
- Retention controls

Free users may see locked evidence/export actions, but the UI must state that
the free playground is not suitable for compliance evidence, long-term
recordkeeping, or regulatory audit use.

## Dashboard Truth Rules

Every visible panel must follow one of these paths:

- Wire to the live backend.
- Show a truthful empty state.
- Disable the action with a clear reason.

Never show fake customers, fake usage, fake revenue, fake invoices, fake
traffic, fake marketplace purchases, or fake identities as if they are real.

## Marketplace Rules

Marketplace listings must be real products, real integrations, real pipeline
packs, or explicitly locked/unavailable Veklom-native offerings.

Install, purchase, and use buttons must either:

- Execute a real flow.
- Link to real source/docs/checkout.
- Be disabled with a clear reason.

## Admin-Only Business Metrics

MRR, churn, marketplace GMV, payout exposure, vendor revenue, and company-level
business metrics are superuser/admin-only. They must not appear in standard
tenant workspace views.

## Live Theater

The landing-page live theater is read-frozen unless a task explicitly targets
that component. Do not redesign, remove, or simplify it during workspace
stabilization.
