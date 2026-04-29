# Deployment Status — sanitized snapshot

## Infrastructure
- Hetzner + Coolify backing infrastructure is provisioned.
- Cloudflare Pages is serving `veklom.com`.
- API and engine services are expected on dedicated subdomains.

## Domain Strategy
- `veklom.com`: public positioning and trust surface.
- `veklom.dev`: marketplace operating surface (signup/login/dashboard).
- `api.veklom.dev` (or `api.veklom.com`): backend API surface.

## Production Checklist (must pass)
- Backend app deployed from `/backend` using `infra/docker/Dockerfile.api`.
- `DATABASE_URL`, `REDIS_URL`, `SECRET_KEY`, `ENCRYPTION_KEY`, Stripe env vars configured in Coolify.
- `alembic upgrade head` executed in production container.
- Stripe webhook points to `/api/v1/subscriptions/webhook` with valid signing secret.
- Smoke tests pass:
  - `GET /health`
  - `GET /status`
  - `POST /api/v1/auth/register` + login flow
  - `POST /api/v1/subscriptions/checkout`

## Coolify Runtime Setup
1. In Coolify, create a new PostgreSQL resource under `Resources -> New Resource -> PostgreSQL`.
2. Copy the generated `DATABASE_URL` from the PostgreSQL resource settings.
3. In Coolify, create a new Redis resource under `Resources -> New Resource -> Redis`.
4. Copy the generated `REDIS_URL` from the Redis resource settings.
5. Open the backend service in Coolify and set:
   - `DATABASE_URL=<coolify_postgres_url>`
   - `REDIS_URL=<coolify_redis_url>`
6. Keep all other secrets in Coolify's secret store:
   - `SECRET_KEY`
   - `ENCRYPTION_KEY`
   - Stripe keys and webhook signing secret
   - any license server admin token
7. Run `alembic upgrade head` once inside the backend container after the first successful start.
8. Smoke test the live service after migration:
   - `GET /health`
   - `GET /status`
   - `POST /api/v1/auth/register`
   - `POST /api/v1/subscriptions/checkout`

## Security Note
- All previously exposed tokens/secrets must be rotated in provider dashboards.
- Keep runtime secrets only in provider secret stores, never in repository files.

## Admin Access Note
- Signed-in workspace owners, admins, and superusers are treated as enterprise for entitlement checks.
- Admin login should therefore expose the full product surface without being blocked by plan gates.
