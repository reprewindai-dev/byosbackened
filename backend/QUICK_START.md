# BYOS AI — Quick Start Guide (Windows)

Get fully running in under 10 minutes.

---

## Prerequisites

| Requirement | Install / Notes |
|---|---|
| Windows 10/11 | x64 required |
| Docker Desktop | https://docker.com/products/docker-desktop — enable WSL2 backend |
| Ollama | https://ollama.com/download — install and let it run in the tray |
| Git | https://git-scm.com |
| Python 3.11+ | Only needed to run tests locally |

---

## Step 1 — Copy Environment File

```powershell
cd backend
Copy-Item .env.example .env
```

Open `.env` and fill in at minimum:

```env
SECRET_KEY=<run: openssl rand -hex 32>
ENCRYPTION_KEY=<run: openssl rand -hex 32>
POSTGRES_PASSWORD=choose_a_strong_password
REDIS_PASSWORD=choose_a_strong_password
```

**Optional but strongly recommended — enables self-healing fallback:**
```env
GROQ_API_KEY=gsk_...   # free at https://console.groq.com
```

**Optional external AI providers:**
```env
OPENAI_API_KEY=sk_...      # for GPT-4/Whisper when selected
HUGGINGFACE_API_KEY=hf_... # for HF models (free tier available)
SERPAPI_KEY=...            # for search functionality
```

Leave everything else as the defaults for local dev.

---

## Step 2 — Start Everything

```powershell
.\start.ps1
```

The script will:
1. Check Ollama is running
2. Pull `qwen2.5:3b` if you don't have it yet (~2GB download, one time)
3. Build Docker images
4. Start Postgres, Redis, MinIO
5. Wait for Postgres to be healthy
6. Run Alembic migrations (`alembic upgrade head`)
7. Seed a dev API key — **the key is printed to your console, copy it**
8. Start the FastAPI server
9. Tail logs

When you see `Application startup complete`, you're live.

---

## Step 3 — Verify It's Working

```powershell
# Health check
curl http://localhost:8000/status

# Landing page
start http://localhost:8000

# Swagger API docs
start http://localhost:8000/api/v1/docs
```

Expected `/status` response:
```json
{
  "db_ok": true,
  "redis_ok": true,
  "llm_ok": true,
  "llm_model": "qwen2.5:3b",
  "groq_fallback_enabled": true,
  "circuit_breaker": { "state": "CLOSED", "failures": 0, "threshold": 3 }
}
```

---

## Step 4 — Make Your First AI Call

Use the dev API key printed during start (format: `byos_xxxxxxxx`):

```powershell
curl -X POST http://localhost:8000/v1/exec `
  -H "X-API-Key: byos_your_key_here" `
  -H "Content-Type: application/json" `
  -d '{"prompt": "Summarise the key risks in a non-disclosure agreement in 3 bullet points."}'
```

Response:
```json
{
  "response": "1. Confidentiality scope...",
  "provider": "ollama",
  "model": "qwen2.5:3b",
  "total_tokens": 287,
  "latency_ms": 1840,
  "log_id": "exec_abc123..."
}
```

---

## Step 5 — Test Conversation Memory

Pass the same `conversation_id` across multiple calls and the backend maintains context:

```powershell
# First message
curl -X POST http://localhost:8000/v1/exec `
  -H "X-API-Key: byos_your_key_here" `
  -H "Content-Type: application/json" `
  -d '{"prompt": "My company name is AcmeCorp.", "conversation_id": "session-001"}'

# Follow-up — backend remembers the context
curl -X POST http://localhost:8000/v1/exec `
  -H "X-API-Key: byos_your_key_here" `
  -H "Content-Type: application/json" `
  -d '{"prompt": "What is my company name?", "conversation_id": "session-001"}'
# Response: "Your company name is AcmeCorp."
```

---

## Choosing a Model

Edit `.env` → `LLM_MODEL_DEFAULT`:

| Your Hardware | Best Model | Why |
|---|---|---|
| i5/i7 + 16GB RAM (CPU only) | `qwen2.5:3b` | Best quality/speed ratio for CPU inference |
| Any GPU with 4GB VRAM | `llama3.2:3b` | Faster, GPU-accelerated |
| GPU with 8GB+ VRAM | `llama3.1:8b` | High quality, 8B parameter |
| GPU with 24GB+ VRAM | `llama3.1:70b` | Near-GPT-4 quality |

Pull any model: `ollama pull <model-name>`

---

## Enabling Self-Healing (Groq Fallback)

1. Get a free Groq key at https://console.groq.com
2. Add to `.env`: `GROQ_API_KEY=gsk_...`
3. Restart: `docker compose -f docker-compose.dev.yml restart api`

Now if Ollama goes down or is unresponsive, the circuit breaker:
- Opens after 3 failures
- Routes all traffic to Groq (`llama-3.1-8b-instant`) instantly
- Probes Ollama every 60 seconds
- Closes the circuit and returns to local inference automatically

The `provider` field in every response tells you whether `"ollama"` or `"groq"` served it.

---

## Connecting Your Applications

BYOS accepts connections from anywhere — CORS is open by default for local dev.

**Connection options:**

| Method | Header | Best For |
|---|---|---|
| API Key | `Authorization: Bearer byos_...` | Server-to-server, scripts, automation |
| JWT Token | `Authorization: Bearer <jwt>` | User sessions, web apps |

**From JavaScript/browser:**
```javascript
const response = await fetch('http://localhost:8000/v1/exec', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer byos_your_key_here'
  },
  body: JSON.stringify({ prompt: "Hello world" })
});
```

**From Python:**
```python
import requests
response = requests.post(
    "http://localhost:8000/v1/exec",
    headers={"Authorization": "Bearer byos_your_key_here"},
    json={"prompt": "Hello world"}
)
```

**Production CORS:** For production, set `CORS_ORIGINS=["https://yourdomain.com"]` in `.env`.

---

## Useful Commands

```powershell
# View live logs
docker compose -f docker-compose.dev.yml logs api -f

# Restart API only (after code change)
docker compose -f docker-compose.dev.yml restart api

# Stop everything
docker compose -f docker-compose.dev.yml down

# Stop and wipe data (fresh start)
docker compose -f docker-compose.dev.yml down -v

# Run migrations manually
docker exec -it byos_api alembic upgrade head

# Open Postgres shell
docker exec -it byos_postgres psql -U byos byos_ai

# Open Redis CLI
docker exec -it byos_redis redis-cli

# Run tests
docker exec -it byos_api pytest tests/test_exec_endpoints.py -v
```

---

## Service URLs (Local Dev)

| Service | URL | Notes |
|---|---|---|
| API + Swagger | http://localhost:8000/api/v1/docs | Interactive API explorer |
| Landing Page | http://localhost:8000 | Public-facing marketing page |
| System Status | http://localhost:8000/status | Health + circuit breaker |
| Prometheus | http://localhost:9090 | Metrics (prod stack) |
| Grafana | http://localhost:3000 | Dashboards (prod stack) |
| MinIO Console | http://localhost:9001 | File storage UI |

---

## Production Deployment

See **[DEPLOYMENT.md](DEPLOYMENT.md)** for:
- DigitalOcean one-command deploy: `bash deploy-digitalocean.sh yourdomain.com`
- Render deploy via `render.yaml`
- SSL/TLS with Certbot
- Nginx reverse proxy config
- Grafana + Prometheus + Loki observability stack

---

## Pre-Production Checklist

- [ ] `SECRET_KEY` — generate with `openssl rand -hex 32` (not the default)
- [ ] `ENCRYPTION_KEY` — separate from SECRET_KEY
- [ ] `POSTGRES_PASSWORD` — strong, not CHANGE_ME
- [ ] `REDIS_PASSWORD` — strong, not CHANGE_ME
- [ ] `GROQ_API_KEY` — set for self-healing fallback
- [ ] `STRIPE_SECRET_KEY` + `STRIPE_WEBHOOK_SECRET` — for billing
- [ ] `CORS_ORIGINS` — set to your actual frontend domain
- [ ] `AGE_VERIFICATION_REQUIRED=true` — if running adult content platform
- [ ] Migrations run: `alembic upgrade head`
- [ ] Test `/status` endpoint returns all green

---

For the full reference — every endpoint, every config variable, every feature workflow — see **[USER_MANUAL.md](USER_MANUAL.md)**.
