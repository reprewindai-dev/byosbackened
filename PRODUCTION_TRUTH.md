# Veklom Production Truth

Last updated: 2026-05-14

This file is the current source of truth for what is allowed to represent Veklom on `https://veklom.com`.

## Non-negotiable `.com` truth

`https://veklom.com` must serve the black/orange Veklom Sovereign Control Node workspace artifact.

The accepted visual system is:

- Deep black background
- Amber/orange primary action color
- Green/teal health and sovereignty status accents
- Veklom Sovereign Control Node sidebar/header
- Operational workspace screens such as Real-time observability, Spend usage invoices, OpenAI-compatible endpoints, Vault, Team, Models, Pipelines, Compliance, Settings

Invalid for production:

- Purple workspace builds
- Dark-blue simplified mimics
- Empty/skeleton marketplace or monitoring pages
- `/uacp` as the production demo/workspace source
- Any UI that only imitates the black/orange artifact but does not come from the accepted artifact below

## Current accepted `.com` artifact

Artifact root:

`C:\Users\antho\OneDrive\Desktop\.windsurf\byosbackened\backend\landing`

Primary shell:

`C:\Users\antho\OneDrive\Desktop\.windsurf\byosbackened\backend\landing\workspace-app.html`

Accepted built asset bundle currently referenced by the production shell/routes:

- `C:\Users\antho\OneDrive\Desktop\.windsurf\byosbackened\backend\landing\workspace-assets\index-EUKZeqk4.js`
- `C:\Users\antho\OneDrive\Desktop\.windsurf\byosbackened\backend\landing\workspace-assets\index-WqgIFi2m.css`

Route shells live at:

- `backend\landing\overview\index.html`
- `backend\landing\playground\index.html`
- `backend\landing\marketplace\index.html`
- `backend\landing\models\index.html`
- `backend\landing\pipelines\index.html`
- `backend\landing\deployments\index.html`
- `backend\landing\vault\index.html`
- `backend\landing\compliance\index.html`
- `backend\landing\monitoring\index.html`
- `backend\landing\billing\index.html`
- `backend\landing\team\index.html`
- `backend\landing\settings\index.html`

## Required production routes

These routes must serve the black/orange artifact, not a rebuilt mimic:

- `https://veklom.com/overview/`
- `https://veklom.com/playground/`
- `https://veklom.com/marketplace/`
- `https://veklom.com/models/`
- `https://veklom.com/pipelines/`
- `https://veklom.com/deployments/`
- `https://veklom.com/vault/`
- `https://veklom.com/compliance/`
- `https://veklom.com/monitoring/`
- `https://veklom.com/billing/`
- `https://veklom.com/team/`
- `https://veklom.com/settings/`

Known correct production visual checks:

- `/monitoring/` shows `Real-time observability`
- `/billing/` shows `Spend - usage - invoices`
- `/deployments/` shows `OpenAI-compatible endpoints`
- `/vault/` shows `Sovereign secret store`
- `/team/` shows `Roles - MFA - sessions - SAML / SCIM`

## Cloudflare Pages

Cloudflare account ID:

`17e4b29893d8c5315f39b929cb8dd960`

Production Pages project:

`veklom`

Production custom domain:

`https://veklom.com`

Production branch:

`main`

Correct deploy model for `.com`:

- Deploy the already-built static artifact from `backend\landing`
- Do not build `frontend\workspace` for `.com`
- Do not deploy `frontend\workspace\dist` to `.com`
- Do not deploy a `veklom-pricing` project for `.com`
- Do not point `.com` at `landing\pricing.html`

Static artifact deploy command when explicitly requested:

```powershell
$env:CLOUDFLARE_API_TOKEN = "<token from secure env>"
npx --yes wrangler@latest pages deploy "C:\Users\antho\OneDrive\Desktop\.windsurf\byosbackened\backend\landing" --project-name veklom --branch main
```

After deploy, purge Cloudflare cache for `veklom.com` if stale content persists.

Do not store Cloudflare API tokens in repo files.

## Coolify / Hetzner / backend infrastructure

Primary Veklom API:

`https://api.veklom.com`

Primary Veklom production server:

- Provider: Hetzner
- Server name: `veklom-prod-1`
- IP: `5.78.135.11`
- SSH: `ssh -F NUL -i ~/.ssh/veklom-deploy root@5.78.135.11`
- Coolify dashboard: `http://5.78.135.11:8000`
- Coolify project: `veklom`
- Coolify app: `veklom-api`

Primary backend dependencies:

- Postgres via Coolify
- Redis via Coolify
- Ollama container: `veklom-ollama`
- Local model: `qwen2.5:0.5b`

ECOBE / CO2 Router engine:

- URL: `https://engine.veklom.com`
- Hetzner IP: `5.78.153.146`
- Coolify dashboard: `http://5.78.153.146:8000`
- Coolify project: `ecobe`
- Coolify app: `ecobe-engine`

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

`codex/workspace-frontend` / PR #19 is not the current `.com` production source of truth. It must not be presented as the active `.com` artifact unless a future explicit migration is approved.

## Backend route truth

The backend is the source of truth for business capability and API behavior.

The `.com` artifact must align with real backend routes and must not invent frontend-only behavior.

Current backend route groups include:

- Auth / JWT / API keys
- Workspace / members / invites
- Marketplace listings / vendors / Stripe checkout
- Monitoring / audit logs / overview
- Compliance checks / evidence
- Vault / API keys / secrets posture
- Models / routing / provider settings
- Pipelines / deployments / execution control
- Billing / subscriptions / token wallet / Stripe
- Cost prediction / autonomous routing / quality prediction / failure risk
- Privacy / content safety / explainability / kill switch

## Operational rules for future agents

1. Do not replace the black/orange `.com` artifact with a generated rebuild.
2. Do not deploy purple, dark-blue, simplified, empty, or mimic workspace builds.
3. Do not treat `frontend\workspace\dist` as the current production `.com` source.
4. Do not treat `veklom-pricing` as the production Pages project for `.com`.
5. Do not expose tokens, secrets, SSH keys, or Cloudflare tokens in docs or commits.
6. If `.com` looks wrong, first verify `backend\landing\workspace-app.html`, route shells, asset filenames, Cloudflare Pages project, and Cloudflare cache.
7. Backend routes are authoritative. Frontend work must map to existing backend capabilities before any new UI is accepted.
