# BYOS Backend - Local Windows + Ollama Setup

## Overview

Production-ready multi-tenant API service that routes ALL LLM inference to local Ollama on Windows. No external providers, no fallbacks - complete local compute with tenant isolation.

## Architecture

```
Apps (AgencyOS, BattleArena, LumiNode)
    ↓
http://localhost:8000/v1/exec
    ↓
BYOS Backend (Docker)
    ↓
PostgreSQL RLS + Redis
    ↓
Local Ollama (Windows Host)
    ↓
llama3.2:1b model
```

## Prerequisites

- Windows 10/11 with Docker Desktop
- Ollama installed and running on http://127.0.0.1:11434
- llama3.2:1b model installed in Ollama

## Quick Start

### 1. Install Ollama Model
```bash
ollama pull llama3.2:1b
ollama list  # Verify installation
```

### 2. Start Services
```bash
# Using Docker Compose
docker-compose -f docker-compose.local.yml up -d

# Or run locally
pip install -r requirements-local.txt
python main.py
```

### 3. Verify Setup
```bash
# Check system status
curl http://localhost:8000/status

# Run test suite
python test-local-ollama.py
```

## API Endpoints

### POST /v1/exec
Execute LLM inference with tenant isolation

**Headers:**
- `X-API-Key`: Tenant-specific API key

**Request:**
```json
{
  "prompt": "What is machine learning?",
  "model": "llama3.2:1b",
  "stream": false,
  "max_tokens": 1000
}
```

**Response:**
```json
{
  "response": "Machine learning is...",
  "model": "llama3.2:1b",
  "tenant_id": "550e8400-e29b-41d4-a716-446655440001",
  "execution_id": "uuid",
  "timestamp": "2026-02-26T...",
  "tokens_generated": 45,
  "execution_time_ms": 1250
}
```

### GET /status
System health and metrics

```json
{
  "uptime_seconds": 3600,
  "db_ok": true,
  "redis_ok": true,
  "llm_ok": true,
  "active_tenants": 3,
  "total_executions": 1250
}
```

## Tenant Configuration

### Pre-configured Tenants

| Tenant | API Key | Daily Limit |
|--------|---------|-------------|
| AgencyOS | `agencyos_key_123` | 1000 |
| BattleArena | `battlearena_key_456` | 2000 |
| LumiNode | `luminode_key_789` | 500 |

### Usage Examples

```python
import requests

# AgencyOS execution
response = requests.post(
    "http://localhost:8000/v1/exec",
    headers={"X-API-Key": "agencyos_key_123"},
    json={"prompt": "Marketing strategy for SaaS"}
)

# BattleArena execution
response = requests.post(
    "http://localhost:8000/v1/exec", 
    headers={"X-API-Key": "battlearena_key_456"},
    json={"prompt": "Game concept for multiplayer arena"}
)
```

## Multi-Tenant Security

### PostgreSQL RLS
- Row Level Security enabled on all tables
- Tenant isolation enforced at database level
- `request.tenant_id` context set per request

### Redis Isolation
- Keys prefixed: `tenant:{tenant_id}:*`
- Daily execution limits per tenant
- Automatic expiration after 24 hours

### API Key Security
- Tenant-specific API keys
- Inactive tenant rejection
- Daily execution limit enforcement

## Environment Configuration

### Required Environment Variables
```bash
DATABASE_URL=postgresql://byos_user:byos_password@localhost:5432/byos_db
REDIS_URL=redis://localhost:6379/0
LLM_BASE_URL=http://host.docker.internal:11434
LLM_MODEL_DEFAULT=llama3.2:1b
LLM_FALLBACK=off
JWT_SECRET=your_jwt_secret_here
LOG_LEVEL=info
```

### Docker Configuration
- Uses `host.docker.internal` to reach Windows host
- Ollama not exposed publicly
- Backend connects to host via Docker networking

## Monitoring & Observability

### Health Checks
- Database connection status
- Redis connection status  
- LLM service availability
- Daily execution metrics

### Logging
- Request/response logging
- Execution metrics per tenant
- Error tracking and debugging
- Performance monitoring

### Database Views
```sql
-- Tenant statistics
SELECT * FROM tenant_stats;

-- Recent executions per tenant
SELECT * FROM executions 
WHERE tenant_id = 'uuid' 
ORDER BY created_at DESC LIMIT 10;
```

## Production Deployment

### Scaling Considerations
- PostgreSQL connection pooling
- Redis clustering for high availability
- Horizontal scaling of API instances
- Load balancer configuration

### Security Hardening
- API key rotation policies
- Database encryption at rest
- Network segmentation
- Rate limiting per tenant

### Backup & Recovery
- PostgreSQL automated backups
- Redis persistence configuration
- Disaster recovery procedures
- Point-in-time recovery

## Troubleshooting

### Common Issues

**Ollama Connection Failed**
```bash
# Verify Ollama is running
curl http://127.0.0.1:11434/api/tags

# Check model availability
ollama list
```

**Database Connection Issues**
```bash
# Check PostgreSQL container
docker logs byos-backend_postgres_1

# Verify database connectivity
docker exec -it postgres psql -U byos_user -d byos_db
```

**Redis Connection Issues**
```bash
# Check Redis container
docker logs byos-backend_redis_1

# Test Redis connectivity
docker exec -it redis redis-cli ping
```

### Performance Optimization

**Database Performance**
- Index optimization for tenant queries
- Connection pool tuning
- Query execution analysis

**LLM Performance**
- Model quantization options
- Batch processing capabilities
- Response caching strategies

**Memory Management**
- Container resource limits
- Garbage collection tuning
- Memory leak detection

## Development

### Local Development Setup
```bash
# Install dependencies
pip install -r requirements-local.txt

# Set environment variables
cp .env.local .env

# Run locally
python main.py
```

### Testing
```bash
# Run test suite
python test-local-ollama.py

# Load testing
python load_test.py
```

### Database Migrations
```bash
# Create new migration
alembic revision --autogenerate -m "Add new feature"

# Apply migrations
alembic upgrade head
```

## Support

### Documentation
- API documentation: http://localhost:8000/docs
- OpenAPI spec: http://localhost:8000/openapi.json
- Database schema: `database/init.sql`

### Monitoring
- Prometheus metrics: `/metrics`
- Health checks: `/health`, `/status`
- Request logs: Container logs

---

**Status**: ✅ Production Ready  
**Architecture**: Multi-tenant, Local LLM, Docker Compose  
**Security**: PostgreSQL RLS, API Key Authentication  
**Performance**: Optimized for local development and scale
