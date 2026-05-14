# veklom.com Production Artifact Lock

Last updated: 2026-05-14

This lock defines what is allowed to represent Veklom on `https://veklom.com`.

## Accepted artifact

The accepted `.com` artifact is the black/orange Veklom Sovereign Control Node static workspace in:

`C:\Users\antho\OneDrive\Desktop\.windsurf\byosbackened\backend\landing`

Primary shell:

`C:\Users\antho\OneDrive\Desktop\.windsurf\byosbackened\backend\landing\workspace-app.html`

Accepted asset bundle:

- `backend\landing\workspace-assets\index-EUKZeqk4.js`
- `backend\landing\workspace-assets\index-WqgIFi2m.css`

## Accepted visual markers

The production artifact must visually match the black/orange source-of-truth screenshots:

- Veklom Sovereign Control Node top-left identity
- Black operating-console background
- Amber/orange buttons and chart lines
- Green/teal live, healthy, sovereign status indicators
- Route screens for observability, billing, endpoints, vault, team, overview, playground, marketplace, models, pipelines, compliance, and settings

## Rejected artifacts

The following are not allowed on `.com`:

- Purple workspace builds
- Dark-blue simplified builds
- Empty route shells
- Marketplace transparency placeholder
- `/uacp` production shell
- Generated rebuilds that merely imitate the artifact
- `frontend\workspace\dist` unless explicitly approved later as a migration
- `veklom-pricing` as the `.com` project
- `landing\pricing.html` as the `.com` root deployment

## Cloudflare production target

Cloudflare account ID:

`17e4b29893d8c5315f39b929cb8dd960`

Project:

`veklom`

Domain:

`https://veklom.com`

Branch:

`main`

Deploy source:

`backend\landing`

## Verification checklist

A valid deployment must satisfy these checks:

- `https://veklom.com/monitoring/` serves `Real-time observability`
- `https://veklom.com/billing/` serves `Spend - usage - invoices`
- `https://veklom.com/deployments/` serves `OpenAI-compatible endpoints`
- `https://veklom.com/vault/` serves `Sovereign secret store`
- `https://veklom.com/team/` serves `Roles - MFA - sessions - SAML / SCIM`
- The served HTML references the accepted asset bundle or the current explicitly approved replacement bundle
- Cloudflare cache is purged after artifact replacement

## Agent rule

If this artifact lock conflicts with older docs, this file wins.
