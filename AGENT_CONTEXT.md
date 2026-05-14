# Agent Context - Veklom Production Truth

Read this before touching Veklom deployment, docs, frontend, or backend.

Last updated: 2026-05-14

## Current objective

Keep `https://veklom.com` aligned with the real black/orange Veklom Sovereign Control Node artifact and the real backend capabilities.

The immediate production truth is documented in:

`C:\Users\antho\OneDrive\Desktop\.windsurf\byosbackened\PRODUCTION_TRUTH.md`

## Non-negotiable product truth

The only accepted `.com` workspace is the black/orange Veklom Sovereign Control Node artifact.

Accepted examples:

- Real-time observability
- Spend - usage - invoices
- OpenAI-compatible endpoints
- Sovereign secret store
- Roles - MFA - sessions - SAML / SCIM
- Sovereign control plane overview
- Visual builder for governed inference
- Operational evidence - not a marketing page

Rejected examples:

- Purple workspace builds
- Dark-blue simplified mimics
- Empty monitoring/marketplace shells
- `/uacp` as production source
- Generated rebuilds that merely imitate the black/orange artifact

## Current `.com` artifact

Artifact root:

`C:\Users\antho\OneDrive\Desktop\.windsurf\byosbackened\backend\landing`

Primary shell:

`C:\Users\antho\OneDrive\Desktop\.windsurf\byosbackened\backend\landing\workspace-app.html`

Current accepted assets:

- `backend\landing\workspace-assets\index-EUKZeqk4.js`
- `backend\landing\workspace-assets\index-WqgIFi2m.css`

Do not replace this with `frontend\workspace\dist` unless Anthony explicitly approves a migration.

## Cloudflare

Cloudflare account ID:

`17e4b29893d8c5315f39b929cb8dd960`

Pages project:

`veklom`

Custom domain:

`https://veklom.com`

Production branch:

`main`

Correct deploy source for `.com`:

`backend\landing`

Wrong deploy sources for `.com`:

- `frontend\workspace\dist`
- `landing\pricing.html`
- `veklom-pricing`
- `codex/workspace-frontend` as if it were current production

## GitHub

Repo:

`reprewindai-dev/byosbackened`

Remote:

`https://github.com/reprewindai-dev/byosbackened.git`

Production branch:

`main`

Historical note:

`codex/workspace-frontend` and PR #19 contain previous work but are not the accepted current `.com` production artifact unless a future migration is explicitly approved.

## Hetzner / Coolify

Veklom API:

`https://api.veklom.com`

Primary Veklom server:

- Hetzner IP: `5.78.135.11`
- Server: `veklom-prod-1`
- SSH: `ssh -F NUL -i ~/.ssh/veklom-deploy root@5.78.135.11`
- Coolify: `http://5.78.135.11:8000`
- Project: `veklom`
- App: `veklom-api`

ECOBE / CO2 Router:

- URL: `https://engine.veklom.com`
- Hetzner IP: `5.78.153.146`
- Coolify: `http://5.78.153.146:8000`
- Project: `ecobe`
- App: `ecobe-engine`

License server:

- URL: `https://license.veklom.com/health`
- Host: `5.78.153.146`

## Backend capability truth

The backend is the source of truth. Any frontend route must map to real backend capability.

Important backend groups:

- Auth, JWT, refresh, API keys
- Workspace members and invites
- Marketplace vendors, listings, uploads, purchases, Stripe checkout
- Monitoring, audit logs, hash verification, overview
- Billing, subscriptions, token wallet, reserves
- Models, routing, cost prediction
- Autonomous cost/quality/failure-risk/routing prediction
- Pipelines and deployments
- Vault/security/privacy/content safety/compliance/explainability
- Kill switch and support flows

## Operating rules

- Do not build unless asked.
- Do not deploy unless asked.
- Do not edit frontend source/CSS unless asked.
- Do not touch backend code during docs-only work.
- Do not expose secrets in docs.
- For `.com` issues, inspect artifact routing, asset filenames, Cloudflare project, branch, and cache before changing code.
