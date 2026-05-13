# BYOS AI — Sovereign AI Infrastructure

**The AI backend that pays for itself.** Local LLM inference, self-healing circuit breaker, autonomous cost intelligence, cryptographic audit trails, content safety, and multi-tenant isolation — one platform that replaces five tools.

**Stack:** Python 3.11 · FastAPI · PostgreSQL (RLS) · Redis · Ollama · Celery · Stripe · Docker

---

## What This Is

BYOS (Bring Your Own Server) is a production-grade AI backend you self-host on your own hardware. Every AI inference request runs locally on your machine via Ollama — no data leaves your server by default. If Ollama fails, a Redis-backed circuit breaker automatically routes to Groq cloud and silently recovers when Ollama comes back online.

Built for industries where data sovereignty isn't optional: adult platforms, legal, healthcare, finance, agencies.

---

## Quick Navigation

| Document | What It Covers |
|---|---|
| **[QUICK_START.md](QUICK_START.md)** | Get running in 5 minutes on Windows |
| **[USER_MANUAL.md](USER_MANUAL.md)** | Complete reference — every feature, endpoint, config |
| **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)** | Production deploy to DigitalOcean or Render |
| **[docs/SECURITY.md](docs/SECURITY.md)** | Zero-trust, encryption, audit logging |
| **[docs/COST_INTELLIGENCE.md](docs/COST_INTELLIGENCE.md)** | Cost prediction, routing, budgets, billing |
| **[docs/PRIVACY.md](docs/PRIVACY.md)** | GDPR, PII detection, data retention |
| **[docs/COMPLIANCE.md](docs/COMPLIANCE.md)** | SOC2, CCPA, compliance reports |
| **[docs/PLUGIN_SYSTEM.md](docs/PLUGIN_SYSTEM.md)** | Adding custom providers and plugins |
| **[docs/COMPETITIVE_ADVANTAGE.md](docs/COMPETITIVE_ADVANTAGE.md)** | Market positioning and differentiators |

---

## 60-Second Overview

```
Request → POST /v1/exec
        ↓
   Circuit Breaker (Redis)
   ├── CLOSED  → Ollama (local, qwen2.5:3b) ──→ response
   ├── OPEN    → Groq cloud (auto-fallback)  ──→ response
   └── HALF-OPEN → probe Ollama → recover silently

   Every execution:
   - Tenant resolved via API key (SHA-256) → RLS applied
   - Conversation history injected from Redis (if conversation_id given)
   - Result logged: tenant, model, provider, tokens, latency, cost
   - HMAC-SHA256 audit record written (immutable)
```

---

## Feature Pillars

| Pillar | Key Capabilities |
|---|---|
| 🧠 **LLM Engine** | Ollama local inference, circuit breaker, Groq fallback, Redis conversation memory |
| 💰 **Cost Intelligence** | Pre-flight cost prediction (95% ±5%), intelligent routing saves 30–70%, budget enforcement, precise billing |
| 🔒 **Security Suite** | Zero-trust middleware, AES-256-GCM, JWT+MFA, RBAC, API keys, security event dashboard |
| 📋 **Compliance + Privacy** | HMAC-SHA256 audit logs, GDPR right to access/delete/port, PII auto-masking, SOC2 reports |
| 🛡️ **Content Safety** | NSFW detection, age verification, CSAM zero-tolerance block, adult content gating |
| 🤖 **Autonomous Intelligence** | ML cost predictor, ML routing optimizer, ML quality predictor, self-training pipeline |
| 📊 **Observability** | Prometheus metrics, Grafana dashboards, Loki logs, system health scoring, incident response |
| 🏗️ **Infrastructure** | Postgres RLS, Redis, MinIO/S3, Celery workers, Stripe billing, plugin system |

---

## Hardware Recommendation (Windows, CPU-only)

| Hardware | Recommended Model | Speed |
|---|---|---|
| i5/i7 + 16GB RAM | `qwen2.5:3b` | ~10–15 tok/s |
| Any GPU 4GB+ | `llama3.2:3b` | ~30–50 tok/s |
| GPU 8GB+ | `llama3.1:8b` | ~20–40 tok/s |

---

## One-Command Start (Windows)

```powershell
# 1. Install Ollama → https://ollama.com/download
# 2. Copy env file and add your keys
cp .env.example .env

# 3. Start everything
.\start.ps1
# → Pulls qwen2.5:3b if missing
# → Starts Postgres, Redis, MinIO, API
# → Runs migrations
# → Seeds dev API key (printed to console)
# → Opens API at http://localhost:8000
```

---

## API Base URLs

| Environment | URL |
|---|---|
| Local dev | `http://localhost:8000` |
| Prod (DigitalOcean) | `https://yourdomain.com` |
| API Docs (Swagger) | `http://localhost:8000/api/v1/docs` |
| Landing Page | `http://localhost:8000/` |
| Health / Status | `http://localhost:8000/status` |

---

## Pricing Tiers (built-in Stripe billing)

| Plan | Price | Calls/mo | Key Features |
|---|---|---|---|
| Starter | $79/mo | 50k | Local inference, circuit breaker, memory, security logs |
| Agency | $249/mo | 500k | + Cost routing, budget enforcement, content filtering, GDPR reports |
| Enterprise | $999/mo | Unlimited | + Age verification, ML optimizer, CSAM blocking, SOC2 audit trail, SLA |

---

## Migration Chain

```
001_add_autonomous_ml_edge_models → 002_security_suite_integration → 003_ollama_exec_multitenant → 004_add_routing_policy_and_missing_tables
```

Run: `docker exec -it byos_api alembic upgrade head`

---

## Tests

```bash
pytest tests/test_exec_endpoints.py -v
```

---

## License Server Monitoring

Use UptimeRobot to watch the public web surface, the routed API, and the license server.

### Monitored URLs

- Marketing site: `https://veklom.com`
- Routed API health: `https://api.veklom.com/health`
- Primary license server: `https://license.veklom.com/health`
- Backup license server (optional): `https://license2.veklom.com/health`

### UptimeRobot Setup

1. Create a free account at `https://uptimerobot.com/`.
2. In the dashboard, click `Add New Monitor`.
3. Set `Monitor Type` to `HTTP(s)`.
4. Set `Friendly Name` to `Veklom Marketing Site`.
5. Set `URL (or IP)` to `https://veklom.com`.
6. Set `Monitoring Interval` to `5 minutes`.
7. Leave the request method as `GET`.
8. Set the optional keyword to `Veklom`.
9. Under `Alert Contacts`, enable your email contact and your SMS contact.
10. Save the monitor.
11. Create a second `HTTP(s)` monitor named `Veklom API Health` for `https://api.veklom.com/health`.
12. Set the optional keyword to `"status":"ok"`.
13. Create a third `HTTP(s)` monitor named `Veklom License Primary` for `https://license.veklom.com/health`.
14. Set the optional keyword to `"status":"ok"`.
15. Create a fourth `HTTP(s)` monitor named `Veklom License Backup` for `https://license2.veklom.com/health` only if the backup host is actually live.

### Alerting Rules

- Alert on the first failed check for each monitor.
- Keep web, API, and primary / backup license monitors separate so you can tell which surface failed.
- Keep recovery alerts enabled so you get a clear restore signal after downtime.

### Response Shape

The license health endpoint returns a JSON payload with:

- `status`
- `server`
- `uptime_seconds`
- `started_at`
- `timestamp`

### Operational Note

- The validator should try the primary verifier first, then the backup verifier, then the local cache grace window.
- UptimeRobot is only detection and alerting. It does not replace application-side failover.
