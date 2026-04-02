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
| **[DEPLOYMENT.md](DEPLOYMENT.md)** | Production deploy to DigitalOcean or Render |
| **[docs/SECURITY.md](docs/SECURITY.md)** | Zero-trust, encryption, audit logging |
| **[docs/COST_INTELLIGENCE.md](docs/COST_INTELLIGENCE.md)** | Cost prediction, routing, budgets, billing |
| **[docs/PRIVACY.md](docs/PRIVACY.md)** | GDPR, PII detection, data retention |
| **[docs/COMPLIANCE.md](docs/COMPLIANCE.md)** | SOC2, CCPA, compliance reports |
| **[docs/PLUGIN_SYSTEM.md](docs/PLUGIN_SYSTEM.md)** | Adding custom providers and plugins |
| **[COMPETITIVE_ADVANTAGE.md](COMPETITIVE_ADVANTAGE.md)** | Market positioning and differentiators |

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
001_initial → 002_security_suite → 003_ollama_exec_multitenant
```

Run: `docker exec -it byos_api alembic upgrade head`

---

## Tests

```bash
pytest tests/test_exec_endpoints.py -v
```
