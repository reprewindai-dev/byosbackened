# Veklom BYOS Backend — Devin Playbook

Read this entire file before touching any code. It defines the stack, conventions, and known issues.

---

## Stack Overview

- **Runtime:** Python 3.11, FastAPI, Gunicorn + Uvicorn workers
- **DB:** PostgreSQL via SQLAlchemy 2.x + psycopg2-binary. Alembic for migrations.
- **Cache:** Redis (hiredis)
- **HTTP client:** httpx[http2] — always use `httpx[http2]`, never bare `httpx`
- **Auth:** JWT-based, workspace-scoped via `core.auth.get_current_workspace`
- **Config:** Pydantic Settings via `core.config.get_settings` — never hardcode env vars
- **Payments:** Stripe — keys in env, never in code
- **Observability:** Sentry via `core.observability.sentry`
- **Deployment:** Hetzner server `165.22.231.161`, managed via Coolify, SSH key = `veklom-deploy`
- **Domain:** `api.veklom.com`

---

## Repo Structure

```
backend/
  apps/api/
    main.py          — FastAPI app, startup/shutdown, middleware stack
    routers/         — one file per feature (ai.py, billing.py, etc.)
    middleware/      — custom middleware (rate_limit, budget_check, locker_security, fast_path, etc.)
    schemas/         — Pydantic request/response models
  deps.py            — shared FastAPI dependencies
core/
  config.py          — settings
  auth.py            — workspace auth
  llm/               — LLM provider wrappers (groq_fallback.py, etc.)
  logging/
  observability/
  security/
db/
  session.py         — engine, SessionLocal, Base
  models/            — SQLAlchemy ORM models
frontend/workspace/  — React/TypeScript frontend
ops/                 — docker-compose, Dockerfiles
```

---

## Critical Conventions

### Database
- **NEVER** use raw `Base.metadata.create_all()` without first guarding ENUM creation.
- Any `CREATE TYPE` must use this pattern:
  ```sql
  DO $$ BEGIN
      CREATE TYPE myenum AS ENUM ('a', 'b');
  EXCEPTION WHEN duplicate_object THEN NULL;
  END $$;
  ```
- Use Alembic for schema changes. Migration files go in `alembic/versions/`.
- `db/session.py` exports: `engine`, `SessionLocal`, `Base`, `get_db`

### HTTP Client
- Always use `httpx[http2]` — it is in `pyproject.toml` dependencies.
- When creating an `httpx.Client`, set `timeout=` explicitly. Default is too low for LLM calls.
- For Groq calls: see `core/llm/groq_fallback.py` — use `_shared_groq_client(timeout_seconds)`

### Routers
- All routers are registered in `apps/api/main.py`
- Prefix pattern: `/api/v1/` is set at app level — routers use relative paths only
- Auth dependency: `workspace: Workspace = Depends(get_current_workspace)`
- Every router must handle its own HTTPException — do not let raw exceptions bubble up

### Middleware Stack (order matters — do not reorder)
1. ZeroTrustMiddleware
2. MetricsMiddleware
3. IntelligentRoutingMiddleware
4. EdgeRoutingMiddleware
5. BudgetCheckMiddleware
6. RateLimitMiddleware
7. EntitlementCheckMiddleware
8. LockerSecurityIntegrationMiddleware
9. RequestSecurityMiddleware
10. PerformanceMiddleware / GzipMiddleware
11. FastPathMiddleware

### LLM / AI
- Primary route: `POST /api/v1/ai/complete` → `apps/api/routers/ai.py` → `_call_runtime_model()`
- Runtime fallback chain: On-prem Ollama → Groq → error
- If on-prem lock is enabled and Ollama is down, fall through to Groq — do NOT throw 503 directly
- `max_tokens` default = 512 (not 64)

### CO2 Router
- Separate repo: `reprewindai-dev/co2router-site`
- Do not mix CO2 Router logic into this backend
- If a task mentions CO2 Router, confirm which repo to work in before starting

### UACP (Universal AI Control Plane)
- Internal router: `apps/api/routers/internal_uacp.py`
- GPC execute endpoint: `POST /api/v1/internal/uacp/command`
- Request body: `{ command: str, prompt: str }`
- Response: `{ status, output, risks, policy_requirements, cost_controls }`

### Billing / Stripe
- Topup checkout: `POST /api/v1/wallet/topup/checkout` → body: `{ package_id, success_url, cancel_url }`
- Response: `{ checkout_url }` — frontend does `window.location.href = checkout_url`
- `STRIPE_SECRET_KEY` must start with `sk_test_` in staging, `sk_live_` in production
- Never hardcode Stripe keys

---

## Known Production Issues (fix these, do not reintroduce)

| Issue | Status | Fix Applied |
|-------|--------|-------------|
| `userrole` ENUM UniqueViolation on startup | Fixed in `main.py` b482b02 | DO $$ EXCEPTION guard |
| `httpx` missing `h2` module on `/ai/complete` | Fixed in `pyproject.toml` a1a36fb | `httpx[http2]` |
| GPC Execute posting to wrong URL | Fixed in `GPCPage.tsx` | `/internal/uacp/command` |
| Gunicorn workers OOM SIGKILL | Ongoing | Separate Ollama from API container |
| Telemetry `/events` 3.6s avg | Ongoing | Batch DB writes |
| FastPath `Content-Length` mismatch on `/marketplace/listings` | Ongoing | Remove manual header |

---

## How to Run Locally

```bash
cd backend
pip install -e '.[dev]'
uvicorn apps.api.main:app --reload --port 8000
```

## Environment Variables Required

```
DATABASE_URL=postgresql://...
REDIS_URL=redis://...
STRIPE_SECRET_KEY=sk_test_...
SENTRY_DSN=...
GROQ_API_KEY=...
SECRET_KEY=...
LICENSE_KEY=...
```

---

## Devin Task Template

When given a task, always:
1. Read this file first
2. Identify the exact file(s) to change
3. Follow existing patterns in adjacent files — do not invent new patterns
4. Add a Sentry breadcrumb or log line for any new error path
5. Do not change middleware order
6. Test with: `pytest backend/tests/` before committing
7. Commit message format: `fix: <what> in <file> — <why>`
