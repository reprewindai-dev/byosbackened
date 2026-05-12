# Veklom Workspace

Sovereign Control Plane — production React frontend for the Veklom backend (`byosbackened`).

## Stack

- Vite 5 + React 18 + TypeScript 5
- TailwindCSS 3 with Veklom ink/bone/brass/moss design tokens
- React Router v6 (browser history)
- TanStack Query v5 for server state
- Zustand for auth + UI state
- axios with token refresh interceptor
- Recharts for telemetry charts
- Stripe.js for checkout
- Lucide React for icons

## Getting started

```bash
cp .env.example .env
# edit .env with your backend URL + stripe publishable key
npm install
npm run dev          # http://localhost:5173 (proxies /api + /v1 to backend)
npm run build        # -> dist/
npm run preview
```

## Environment

| Variable | When | Notes |
|---|---|---|
| `VITE_UACP_BACKEND_BASE_URL` | build-time | Canonical backend base for UACP owner/operator routes. Takes precedence over legacy `VITE_VEKLOM_API_BASE`. |
| `VITE_VEKLOM_API_BASE` | build-time | Baked into bundle. e.g. `https://api.veklom.com` |
| `VITE_VEKLOM_API_BASE_DEV` | dev-only | Dev-server proxy target. Defaults to `http://localhost:8000` |
| `VITE_STRIPE_PUBLISHABLE_KEY` | build-time | Stripe.js publishable key |
| `window.__VEKLOM_API_BASE__` | runtime | Overrides `VITE_VEKLOM_API_BASE` at runtime via `public/config.js` — rewrite at deploy time for multi-env |
| `window.__UACP_BACKEND_BASE_URL__` | runtime | Canonical runtime override for the protected backend bridge. Takes precedence over `window.__VEKLOM_API_BASE__`. |
| `window.__VEKLOM_STRIPE_PK__` | runtime | Overrides Stripe PK at runtime |

The runtime-override pattern (`config.js`) allows one build artifact to ship to staging + production without rebuilding.

## Deploy

### Cloudflare Pages (recommended — matches existing `_headers` and `_redirects`)

```
Build command:   npm run build
Build output:    dist
Environment:     VITE_UACP_BACKEND_BASE_URL=https://api.veklom.com
Rewrites:        handled by public/_redirects (SPA fallback)
Headers:         handled by public/_headers
```

At deploy time, replace `dist/config.js` to inject per-environment runtime values.

### Coolify (alternative — serve alongside backend)

1. Add a new "Static Site" resource in Coolify pointing at `frontend/workspace`
2. Build command: `npm install && npm run build`
3. Publish directory: `dist`
4. Set `VITE_UACP_BACKEND_BASE_URL=https://api.veklom.com` in Coolify env
5. Add a Caddyfile or nginx config serving `index.html` as SPA fallback

## Folder layout

```
src/
  lib/            api client, auth, utility hooks
  store/          zustand stores
  types/          shared TypeScript types
  components/
    layout/       AppShell, TopBar, Sidebar, FooterRail
    ui/           primitives (Button, Card, Badge, Input, ...)
  pages/          one file per route
  routes.tsx      route table
  main.tsx        entry
  App.tsx         providers + router host
  index.css       tailwind directives + global tokens
```

## Auth contract

- `POST /api/v1/auth/login` → `{ access_token, refresh_token, token_type, expires_in }`
- Access token stored in memory; refresh token in `httpOnly` cookie OR `localStorage` (configurable)
- axios interceptor catches 401, runs `POST /api/v1/auth/refresh`, retries original request
- On refresh failure → logout + redirect to `/login`

## Roadmap (active)

See `/BACKEND_API_INVENTORY.md` at repo root for the full frontend↔backend endpoint map.

Each screen lands as a separate PR:

1. ✅ Scaffold + auth shell + Overview (this PR)
2. Playground (SSE, sessions, tools, policy, audit export)
3. Vault (secrets CRUD, rotation, HSM seal)
4. Marketplace (listings, checkout via Stripe Connect, vendor dashboard)
5. Team & Access (RBAC, MFA, SAML/SCIM)
6. Compliance (frameworks, evidence, packs)
7. Monitoring (metrics, alerts, security events)
8. Billing (invoices, wallet, subscriptions)
9. Settings (workspace, routing, integrations, danger zone)
