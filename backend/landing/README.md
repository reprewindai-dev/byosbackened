# Veklom Landing + Marketplace Surface

This directory is the production static web surface for:

- `veklom.com` (public trust/positioning page)
- `veklom.dev` (marketplace operating surface with signup/login/dashboard)

## Included routes

- `/` marketing page
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
