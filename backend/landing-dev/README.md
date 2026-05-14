# Veklom Landing + Site Split Surface

This directory is the production static web surface for:

- `veklom.com` (buyer-facing Veklom Sovereign AI Hub + GPC demo)
- `veklom.dev` (legacy live backend demo at `/` + developer/BYOS backend proof at `/platform/`)

## Messaging authority lock

- Canonical public copy source is `COPY_LOCK_ISSUE1.md`.
- Required `.com` hierarchy is buyer Hub first: Playground, GPC / Plan Compiler, Models, Tools, Pipelines, Governance, Deployments, Monitoring.
- Required `.dev` hierarchy is technical proof first: BYOS backend, legacy integrations, API/backend health, license/access flow, tenant isolation, private deployment, policy/fallback/routing, archive/evidence/replay.
- Marketplace/Tools is one module inside the hub. Do not describe Veklom itself as a marketplace.

## Included routes

- `/` legacy live backend demo:
  - `veklom.dev` opens directly on the BYOS/legacy live backend execution theater.
- `/platform/` developer/BYOS proof page:
  - technical integration, runtime, contract, route, license, isolation, evidence, and replay positioning.
- `/signup/` self-serve workspace creation
- `/login/` authentication
- `/dashboard/` API key + subscription management
- `/blog/` field notes
- `/legal/` legal pages

## API integration

Frontend auth/billing calls are handled by `app/auth.js`:

- `*.veklom.dev` -> `https://api.veklom.dev/api/v1`
- default -> `https://api.veklom.com/api/v1`

You can override at runtime with `window.VEKLOM_API`.

## Deploy model

- Static assets deploy from this folder to Cloudflare Pages.
- Backend can also serve this folder directly (FastAPI mounts `landing/` at `/`).
- `_headers` and `_redirects` are required for security headers and canonical URL behavior.

## Non-negotiables

- Do not commit real secrets into any `.env*` file in this repo.
- Keep pricing in sync with:
  - `landing/index.html`
  - `apps/api/routers/subscriptions.py`
  - `PRICING_TRUTH.md`
- Keep public phrasing in sync with:
  - `landing/COPY_LOCK_ISSUE1.md`
