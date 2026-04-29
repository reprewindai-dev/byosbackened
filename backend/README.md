# BYOS AI â€” Sovereign AI Infrastructure

**The AI backend that pays for itself.** Local LLM inference, self-healing circuit breaker, autonomous cost intelligence, cryptographic audit trails, content safety, and multi-tenant isolation â€” one platform that replaces five tools.

**Stack:** Python 3.11 Â· FastAPI Â· PostgreSQL (RLS) Â· Redis Â· Ollama Â· Celery Â· Stripe Â· Docker

---

## What This Is

BYOS (Bring Your Own Server) is a production-grade AI backend you self-host on your own hardware. Every AI inference request runs locally on your machine via Ollama â€” no data leaves your server by default. If Ollama fails, a Redis-backed circuit breaker automatically routes to Groq cloud and silently recovers when Ollama comes back online.

Built for industries where data sovereignty isn't optional: adult platforms, legal, healthcare, finance, agencies.

---

## Quick Navigation

| Document | What It Covers |
|---|---|
| **[QUICK_START.md](QUICK_START.md)** | Get running in 5 minutes on Windows |
| **[USER_MANUAL.md](USER_MANUAL.md)** | Complete reference â€” every feature, endpoint, config |
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
Request â†’ POST /v1/exec
        â†“
   Circuit Breaker (Redis)
   â”œâ”€â”€ CLOSED  â†’ Ollama (local, qwen2.5:3b) â”€â”€â†’ response
   â”œâ”€â”€ OPEN    â†’ Groq cloud (auto-fallback)  â”€â”€â†’ response
   â””â”€â”€ HALF-OPEN â†’ probe Ollama â†’ recover silently

   Every execution:
   - Tenant resolved via API key (SHA-256) â†’ RLS applied
   - Conversation history injected from Redis (if conversation_id given)
   - Result logged: tenant, model, provider, tokens, latency, cost
   - HMAC-SHA256 audit record written (immutable)
```

---

## Feature Pillars

| Pillar | Key Capabilities |
|---|---|
| ðŸ§  **LLM Engine** | Ollama local inference, circuit breaker, Groq fallback, Redis conversation memory |
| ðŸ’° **Cost Intelligence** | Pre-flight cost prediction (95% Â±5%), intelligent routing saves 30â€“70%, budget enforcement, precise billing |
| ðŸ”’ **Security Suite** | Zero-trust middleware, AES-256-GCM, JWT+MFA, RBAC, API keys, security event dashboard |
| ðŸ“‹ **Compliance + Privacy** | HMAC-SHA256 audit logs, GDPR right to access/delete/port, PII auto-masking, SOC2 reports |
| ðŸ›¡ï¸ **Content Safety** | NSFW detection, age verification, CSAM zero-tolerance block, adult content gating |
| ðŸ¤– **Autonomous Intelligence** | ML cost predictor, ML routing optimizer, ML quality predictor, self-training pipeline |
| ðŸ“Š **Observability** | Prometheus metrics, Grafana dashboards, Loki logs, system health scoring, incident response |
| ðŸ—ï¸ **Infrastructure** | Postgres RLS, Redis, MinIO/S3, Celery workers, Stripe billing, plugin system |

---

## Hardware Recommendation (Windows, CPU-only)

| Hardware | Recommended Model | Speed |
|---|---|---|
| i5/i7 + 16GB RAM | `qwen2.5:3b` | ~10â€“15 tok/s |
| Any GPU 4GB+ | `llama3.2:3b` | ~30â€“50 tok/s |
| GPU 8GB+ | `llama3.1:8b` | ~20â€“40 tok/s |

---

## One-Command Start (Windows)

```powershell
# 1. Install Ollama â†’ https://ollama.com/download
# 2. Copy env file and add your keys
cp .env.example .env

# 3. Start everything
.\start.ps1
# â†’ Pulls qwen2.5:3b if missing
# â†’ Starts Postgres, Redis, MinIO, API
# â†’ Runs migrations
# â†’ Seeds dev API key (printed to console)
# â†’ Opens API at http://localhost:8000
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
001_add_autonomous_ml_edge_models â†’ 002_security_suite_integration â†’ 003_ollama_exec_multitenant â†’ 004_add_routing_policy_and_missing_tables
```

Run: `docker exec -it byos_api alembic upgrade head`

---

## Tests

```bash
pytest tests/test_exec_endpoints.py -v
```

---

## License Server Monitoring

Use UptimeRobot to watch the public license endpoints and the status endpoint.

### Monitored URLs

- Primary license server: `https://license.veklom.com/health`
- Backup license server: `https://license2.veklom.com/health`
- Status page endpoint: `https://status.veklom.com/health`

### UptimeRobot Setup

1. Create a free account at `https://uptimerobot.com/`.
2. In the dashboard, click `Add New Monitor`.
3. Set `Monitor Type` to `HTTP(s)`.
4. Set `Friendly Name` to `Veklom License Primary`.
5. Set `URL (or IP)` to `https://license.veklom.com/health`.
6. Set `Monitoring Interval` to `5 minutes`.
7. Leave the request method as `GET`.
8. Under `Alert Contacts`, enable your email contact and your SMS contact.
9. Save the monitor.
10. Create a second `HTTP(s)` monitor named `Veklom License Backup` for `https://license2.veklom.com/health`.
11. Use the same `5 minutes` interval and the same email + SMS alert contacts.
12. Create a third `HTTP(s)` monitor named `Veklom Status Endpoint` for `https://status.veklom.com/health`.
13. If you are using UptimeRobot Status Pages, show the `status`, `uptime_seconds`, and `timestamp` fields from the health response.

### Alerting Rules

- Alert on the first failed check for each license endpoint.
- Keep primary and backup monitors separate so you can tell which host failed.
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
