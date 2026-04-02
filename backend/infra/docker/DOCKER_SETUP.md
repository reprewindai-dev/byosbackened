# Docker Compose Setup Guide

## Overview

This directory contains Docker Compose configurations for deploying the BYOS AI Backend:

- **`docker-compose.yml`** - Base compose file with core services (postgres, redis, minio, api, worker)
- **`docker-compose.regions.yml`** - Multi-region extension (extends base services for US-East, EU-West, Asia-Pacific)

## Quick Start

### 1. Set Up Environment Variables

Copy the example environment file and configure it:

```bash
cd backend
cp .env.example .env
```

**Required Environment Variables** (minimum to start):

```bash
# Database (uses defaults from docker-compose.yml if not set)
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/byos_ai

# Redis (uses defaults from docker-compose.yml if not set)
REDIS_URL=redis://redis:6379/0

# S3/MinIO (uses defaults from docker-compose.yml if not set)
S3_ENDPOINT_URL=http://minio:9000
S3_ACCESS_KEY_ID=minioadmin
S3_SECRET_ACCESS_KEY=minioadmin
S3_BUCKET_NAME=byos-ai

# Security (REQUIRED - generate a secure key)
SECRET_KEY=your-secret-key-here  # Generate with: openssl rand -hex 32

# AI Providers (at least one required)
HUGGINGFACE_API_KEY=your_hf_token_here
SERPAPI_KEY=your_serpapi_key_here
```

### 2. Start Core Services Only

For initial setup and testing:

```bash
cd infra/docker
docker compose up -d postgres redis minio
```

This starts:
- **PostgreSQL** on port 5432
- **Redis** on port 6379
- **MinIO** on ports 9000 (API) and 9001 (Console)

### 3. Start API Service

```bash
docker compose --profile api up -d
```

This starts the API service on port 8000.

### 4. Start Worker Service

```bash
docker compose --profile worker up -d
```

Or start both API and Worker together:

```bash
docker compose --profile api --profile worker up -d
```

### 5. Start All Services

```bash
docker compose --profile all up -d
```

## Service Details

### Core Services (Always Run)

- **postgres** - PostgreSQL 15 database
  - Port: 5432
  - Database: `byos_ai`
  - User: `postgres` / Password: `postgres`
  - Volume: `postgres_data`

- **redis** - Redis 7 cache and message broker
  - Port: 6379
  - Volume: `redis_data`

- **minio** - MinIO S3-compatible object storage
  - API Port: 9000
  - Console Port: 9001
  - Access Key: `minioadmin`
  - Secret Key: `minioadmin`
  - Volume: `minio_data`

### Application Services

- **api** - FastAPI/Uvicorn API server
  - Port: 8000
  - Profile: `api` or `all`
  - Health: http://localhost:8000/health
  - Docs: http://localhost:8000/api/v1/docs

- **worker** - Celery worker for background tasks
  - Profile: `worker` or `all`
  - Connects to Redis for task queue

## Multi-Region Deployment

To deploy to multiple regions, use the regions compose file:

```bash
docker compose -f docker-compose.yml -f docker-compose.regions.yml up -d
```

This creates:
- `api-us-east` on port 8001
- `api-eu-west` on port 8002
- `api-asia-pacific` on port 8003
- Corresponding worker instances for each region

**Note:** For production multi-region deployment, you would:
1. Deploy each region to separate infrastructure
2. Configure region-specific environment variables:
   - `DATABASE_URL_US_EAST`
   - `REDIS_URL_US_EAST`
   - `S3_ENDPOINT_URL_US_EAST`
   - (and similar for EU-West and Asia-Pacific)

## Environment Variables

### Required for Basic Operation

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://postgres:postgres@postgres:5432/byos_ai` |
| `REDIS_URL` | Redis connection string | `redis://redis:6379/0` |
| `S3_ENDPOINT_URL` | MinIO/S3 endpoint | `http://minio:9000` |
| `SECRET_KEY` | Secret key for JWT/signing | **Required** (no default) |

### Required for AI Features

| Variable | Description | Required |
|----------|-------------|----------|
| `HUGGINGFACE_API_KEY` | Hugging Face API token | Yes (primary) |
| `SERPAPI_KEY` | SERP API key for search | Yes |

### Optional

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key | (empty) |
| `S3_ACCESS_KEY_ID` | S3 access key | `minioadmin` |
| `S3_SECRET_ACCESS_KEY` | S3 secret key | `minioadmin` |
| `S3_BUCKET_NAME` | S3 bucket name | `byos-ai` |
| `DEBUG` | Enable debug mode | `false` |

See `.env.example` for complete list of all environment variables.

## Common Commands

### View Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f api
docker compose logs -f worker
```

### Stop Services

```bash
# Stop all
docker compose down

# Stop and remove volumes (⚠️ deletes data)
docker compose down -v
```

### Restart Service

```bash
docker compose restart api
docker compose restart worker
```

### Run Database Migrations

```bash
docker exec -it byos_api alembic upgrade head
```

### Access MinIO Console

1. Start MinIO: `docker compose up -d minio`
2. Open browser: http://localhost:9001
3. Login with: `minioadmin` / `minioadmin`
4. Create bucket: `byos-ai` (or set `S3_BUCKET_NAME`)

### Access PostgreSQL

```bash
docker exec -it byos_postgres psql -U postgres -d byos_ai
```

### Access Redis CLI

```bash
docker exec -it byos_redis redis-cli
```

## Troubleshooting

### Issue: "Service 'api' not found" or "Service 'worker' not found"

**Solution:** Make sure you're using profiles:
```bash
docker compose --profile api up -d
```

### Issue: Missing environment variables warning

**Solution:** Set the required variables in `.env` file or export them:
```bash
export DATABASE_URL=postgresql://postgres:postgres@postgres:5432/byos_ai
export REDIS_URL=redis://redis:6379/0
export S3_ENDPOINT_URL=http://minio:9000
export SECRET_KEY=$(openssl rand -hex 32)
```

### Issue: Port already in use

**Solution:** Change ports in `docker-compose.yml` or stop conflicting services:
```bash
# Check what's using the port
netstat -ano | findstr :8000  # Windows
lsof -i :8000  # Linux/Mac
```

### Issue: Services won't start

**Solution:** Check logs and health checks:
```bash
docker compose logs
docker compose ps
```

## Production Considerations

1. **Change default passwords** - Update postgres, redis, and minio credentials
2. **Use secrets management** - Don't hardcode secrets in compose files
3. **Enable SSL** - Set `S3_USE_SSL=true` and configure SSL certificates
4. **Resource limits** - Add memory/CPU limits to services
5. **Backup strategy** - Set up regular backups for postgres and minio volumes
6. **Monitoring** - Configure Prometheus metrics and alerting
7. **Logging** - Set up centralized logging (ELK, Loki, etc.)

## File Structure

```
infra/docker/
├── docker-compose.yml          # Base compose (core + api + worker)
├── docker-compose.regions.yml  # Multi-region extension
├── Dockerfile.api              # API service Dockerfile
├── Dockerfile.worker           # Worker service Dockerfile
└── DOCKER_SETUP.md             # This file
```
