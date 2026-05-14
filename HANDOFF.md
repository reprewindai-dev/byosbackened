# Veklom Handoff - Current Production State

Last updated: 2026-05-14

## Current status

`https://veklom.com` must serve the black/orange Veklom Sovereign Control Node artifact from `backend\landing`.

The old docs that described a pricing-page-only deploy, `veklom-pricing`, or `frontend\workspace\dist` as the `.com` artifact are stale and no longer authoritative.

## Production truth doc

Canonical doc:

`C:\Users\antho\OneDrive\Desktop\.windsurf\byosbackened\PRODUCTION_TRUTH.md`

Read that first before touching routing, deploys, frontend, backend, or Cloudflare.

## Correct `.com` deployment target

Cloudflare Pages:

- Account ID: `17e4b29893d8c5315f39b929cb8dd960`
- Project: `veklom`
- Domain: `https://veklom.com`
- Branch: `main`
- Static source: `backend\landing`

Accepted production artifact:

- Shell: `backend\landing\workspace-app.html`
- JS: `backend\landing\workspace-assets\index-EUKZeqk4.js`
- CSS: `backend\landing\workspace-assets\index-WqgIFi2m.css`

Required routes:

- `/overview/`
- `/playground/`
- `/marketplace/`
- `/models/`
- `/pipelines/`
- `/deployments/`
- `/vault/`
- `/compliance/`
- `/monitoring/`
- `/billing/`
- `/team/`
- `/settings/`

## Current visual acceptance checks

Correct:

- `/monitoring/` shows `Real-time observability`
- `/billing/` shows `Spend - usage - invoices`
- `/deployments/` shows `OpenAI-compatible endpoints`
- `/vault/` shows `Sovereign secret store`
- `/team/` shows `Roles - MFA - sessions - SAML / SCIM`

Wrong:

- Purple workspace
- Dark-blue simplified workspace
- Empty marketplace/monitoring shell
- `Marketplace transparency` placeholder page
- `/uacp` as a production source

## Backend / Coolify / Hetzner

Primary API:

`https://api.veklom.com`

Veklom production server:

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

## GitHub

Repository:

`reprewindai-dev/byosbackened`

Remote:

`https://github.com/reprewindai-dev/byosbackened.git`

Production branch:

`main`

Historical branch note:

`codex/workspace-frontend` / PR #19 is not the current `.com` production artifact. Do not tell Anthony that branch is what is live unless a future explicit migration happens.

## What not to do

- Do not build a replacement workspace.
- Do not mimic the black/orange UI.
- Do not deploy purple/dark-blue/simplified workspace builds.
- Do not deploy `frontend\workspace\dist` to `.com`.
- Do not route `.com` through `veklom-pricing`.
- Do not say `.com` needs `landing\pricing.html` as its main deploy.
- Do not expose Cloudflare tokens, SSH keys, Stripe keys, or env secrets in docs.

## If `.com` shows the wrong app

Check in this order:

1. `backend\landing\workspace-app.html` references the accepted JS/CSS bundle.
2. Route shells under `backend\landing\<route>\index.html` point to `workspace-app.html` or accepted assets.
3. Cloudflare Pages project is `veklom`, branch `main`, deploy source `backend\landing`.
4. Cloudflare cache has been purged.
5. Browser cache is bypassed with a query string such as `?cache_bust=<timestamp>`.

Only after those checks should source code changes be considered.
