# Quick Start Guide

## What You've Built

A **secure, future-proof, cost-intelligent AI backend** with:

1. **Cost Intelligence** - Predict costs, route intelligently, track budgets
2. **Compliance** - GDPR-ready audit trails, PII protection
3. **Security** - Zero-trust, encryption, secrets management
4. **Privacy** - Privacy-by-design, data retention, right to deletion
5. **Future-Proofing** - Plugin system, provider abstraction, regulatory framework
6. **Innovation** - Quality scoring, explainability, real-time optimization

## Getting Started

### 1. Configure Environment

```bash
cd backend
cp .env.example .env
# Edit .env with your API keys
```

**Required**:
- `HUGGINGFACE_API_KEY` - Get from https://huggingface.co/settings/tokens
- `SERPAPI_KEY` - Get from https://serpapi.com/dashboard
- `SECRET_KEY` - Generate with: `openssl rand -hex 32`

**Optional**:
- `OPENAI_API_KEY` - Only if you need OpenAI (must be documented)

### 2. Start Services (Modular)

The Docker setup is **truly modular** - start only what you need:

#### Start All Services

```bash
cd infra/docker
docker compose --profile all up -d
```

#### Start Core + API Only (Development)

```bash
docker compose --profile api up -d
```

#### Start Core + API + Worker (Production)

```bash
docker compose --profile api --profile worker up -d
```

#### Start with Self-Hosted AI

```bash
docker compose --profile api --profile worker --profile whisper --profile llm up -d
```

**Available Services**:
- **Core** (always runs): postgres, redis, minio
- **Application**: api, worker, caddy
- **Optional AI**: whisper, llm

See `infra/scripts/MODULAR_SERVICES.md` for full guide.

### 3. Run Migrations

```bash
docker exec -it byos_api alembic upgrade head
```

### 4. Access API

- **API Docs**: http://localhost:8000/api/v1/docs (or http://localhost/api/v1/docs with Caddy)
- **Health**: http://localhost:8000/health
- **Metrics**: http://localhost:8000/metrics

## First Steps

### 1. Create Workspace

```bash
# Via API (requires auth token)
POST /api/v1/workspaces
{
  "name": "My Workspace",
  "slug": "my-workspace"
}
```

### 2. Test Cost Prediction

```bash
POST /api/v1/cost/predict
{
  "operation_type": "transcribe",
  "provider": "huggingface",
  "input_text": "This is a test transcription..."
}

# Response shows predicted cost, confidence interval, alternatives
```

### 3. Test Intelligent Routing

```bash
POST /api/v1/routing/test
{
  "operation_type": "transcribe",
  "constraints": {
    "strategy": "cost_optimized",
    "max_cost": "0.002"
  }
}

# Response shows selected provider and reasoning
```

### 4. Set Budget

```bash
POST /api/v1/budget
{
  "budget_type": "monthly",
  "amount": "100.00",
  "alert_thresholds": [50, 80, 95]
}
```

### 5. Upload and Transcribe

```bash
# Upload file
POST /api/v1/upload
# (multipart form with file)

# Transcribe
POST /api/v1/transcribe
{
  "asset_id": "...",
  "provider": "huggingface"
}

# Check job status
GET /api/v1/jobs/{job_id}
```

## Service Management

### Start/Stop Individual Services

```bash
# Start single service
docker compose --profile api up -d api

# Stop single service
docker compose stop api

# Restart service
docker compose restart api

# View logs
docker compose logs api -f
```

### Helper Scripts (Linux/Mac)

```bash
# Start all enabled services
./infra/scripts/start-services.sh

# Start single service
./infra/scripts/start-service.sh api

# Check status
./infra/scripts/status.sh
```

### Helper Scripts (Windows PowerShell)

```powershell
# Start all enabled services
.\infra\scripts\start-services.ps1
```

## Key Features to Test

### Cost Intelligence

1. **Predict cost** before operation
2. **Route intelligently** to save money
3. **Track budget** and get alerts
4. **Allocate costs** to projects/clients
5. **Generate billing reports**

### Compliance

1. **Export data** (GDPR right to access)
2. **Delete data** (GDPR right to deletion)
3. **Detect PII** in text
4. **Query audit logs**
5. **Generate compliance reports**

### Security

1. **All requests authenticated** (zero-trust)
2. **Secrets encrypted** in database
3. **Security events logged**
4. **Rate limiting** enforced

### Privacy

1. **PII automatically detected**
2. **Data retention** policies enforced
3. **Privacy endpoints** available

## Production Checklist

Before deploying to production:

- [ ] Set strong `SECRET_KEY` (generate with `openssl rand -hex 32`)
- [ ] Set `ENCRYPTION_KEY` (different from SECRET_KEY)
- [ ] Configure domain in Caddyfile
- [ ] Set up API keys (HF, SERP, optional OpenAI)
- [ ] Configure backups (cron for `backup.sh`)
- [ ] Set up monitoring (health endpoint, metrics)
- [ ] Test restore procedure
- [ ] Review security settings
- [ ] Configure data retention policies
- [ ] Set up alerting
- [ ] Choose service profiles (start only what you need)

## Documentation

- `README.md` - Overview and architecture
- `DEPLOYMENT.md` - Production deployment guide
- `infra/scripts/MODULAR_SERVICES.md` - Service management guide
- `docs/SECURITY.md` - Security architecture
- `docs/PRIVACY.md` - Privacy protection
- `docs/COST_INTELLIGENCE.md` - Cost features
- `docs/COMPLIANCE.md` - Compliance features
- `docs/PLUGIN_SYSTEM.md` - Plugin development
- `IMPLEMENTATION_SUMMARY.md` - What was built
- `COMPETITIVE_ADVANTAGE.md` - What sets us apart

## Support

See `STRATEGY.md` for market positioning and business model.

---

**You now have a production-ready, secure, compliant, cost-intelligent AI backend that sets you apart from the competition.**

**Modular by design - run what you need, when you need it.**
