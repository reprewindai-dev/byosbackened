# Deployment Status - live snapshot

## Current Live State
- `api.veklom.com/health` returns `{"status":"ok","version":"1.0.0","service":"Veklom"}`.
- The routed Veklom Coolify container is healthy: `zjhp30ys1jlk8yaoxc96h2zd-213941724689`.
- The license service at `https://license.veklom.com/health` returns `200` after the 2026-05-10 rebuild.
- Production Alembic state was verified on 2026-05-10 at revision `013`, which matches repo head.
- AWS runtime vars are present in the live service env: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION=us-east-1`, and `S3_BACKUP_BUCKET=veklom-db-backups`.
- The stale `9493aceb` note was incorrect. The current non-routed Coolify restart-loop artifact is `lcile2sz1wjd6sqsdctlm4rv-033401126260`, built from commit `9636805d`, and should be treated as a failed deploy artifact until Coolify is reconciled.
- `veklom.dev` is live on Cloudflare Pages and attached to the acquisition / marketplace entry surface.

## Infrastructure
- Hetzner + Coolify backing infrastructure is provisioned.
- Cloudflare Pages is serving `veklom.com`.
- `veklom.dev` is live on Cloudflare Pages.
- API and engine services are expected on dedicated subdomains.

## Domain Strategy
- `veklom.com`: public positioning and trust surface.
- `veklom.dev`: acquisition, signup, login, and dashboard entry surface.
- `api.veklom.com`: backend API surface.
- `engine.veklom.com`: CO2 Router surface.

## Production Checklist (must pass)
- Backend app deployed from `/backend` using `infra/docker/Dockerfile.api`.
- `DATABASE_URL`, `REDIS_URL`, `SECRET_KEY`, `ENCRYPTION_KEY`, Stripe env vars configured in Coolify.
- `alembic upgrade head` executed in production container, and `alembic_version` matches repo head (`013` at last verification).
- Stripe webhook points to `/api/v1/subscriptions/webhook` with valid signing secret.
- License env points at canonical endpoints:
  - `LICENSE_ISSUE_URL=https://license.veklom.com/api/licenses/issue`
  - `LICENSE_VERIFY_URL=https://license.veklom.com/api/licenses/verify`
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
8. Run `python scripts/validate_production.py` inside the runtime and confirm the database check reports current Alembic revision equals repo head.
9. Smoke test the live service after migration:
   - `GET /health`
   - `GET /status`
   - `POST /api/v1/auth/register`
   - `POST /api/v1/subscriptions/checkout`

## Agent Access Map
Use these exact access paths when the backend needs hands-on runtime work:

- Veklom production host: `ssh -F NUL -i ~/.ssh/veklom-deploy root@5.78.135.11`
- CO2 Router / ECOBE host: `ssh -F NUL -i ~/.ssh/veklom-deploy root@5.78.153.146`
- Veklom Coolify app: `veklom-api`
- Veklom Coolify project: `veklom`
- Veklom server resources: PostgreSQL + Redis are already running on `5.78.135.11`
- CO2 Router server resources: PostgreSQL + Redis are already running on `5.78.153.146`
- Coolify dashboard listens on port `8000` on each host when the server is up
- Canonical handoff doc: `backend/docs/AGENT_ACCESS.md`

If a future deploy crashes on startup, check the active container logs on the host before assuming the repo is broken. On the Veklom host, the live app container is the `veklom-api` resource; a restart-looping container can exist beside it during a failed deploy.

## Security Note
- All previously exposed tokens/secrets must be rotated in provider dashboards.
- Keep runtime secrets only in provider secret stores, never in repository files.

## Admin Access Note
- Signed-in workspace owners, admins, and superusers are treated as enterprise for entitlement checks.
- Admin login should therefore expose the full product surface without being blocked by plan gates.
