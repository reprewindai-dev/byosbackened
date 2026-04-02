# Quick Start - Docker Compose Setup

## Problem Solved ✅

You had two issues:
1. ❌ Missing base `docker-compose.yml` file (only had `docker-compose.regions.yml`)
2. ❌ Missing required environment variables

## Solution ✅

### 1. Base Docker Compose File Created

**Location:** `infra/docker/docker-compose.yml`

This file contains:
- ✅ **Core services**: `postgres`, `redis`, `minio` (always run)
- ✅ **API service**: `api` (extends base, runs on port 8000)
- ✅ **Worker service**: `worker` (extends base, processes background tasks)

### 2. Environment Variables Setup

**Required variables** (minimum to start):

```bash
# Copy the example file
cd backend
cp .env.example .env
```

**Edit `.env` and set these required values:**

```bash
# Database (defaults work for Docker Compose)
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/byos_ai

# Redis (defaults work for Docker Compose)
REDIS_URL=redis://redis:6379/0

# S3/MinIO (defaults work for Docker Compose)
S3_ENDPOINT_URL=http://minio:9000
S3_ACCESS_KEY_ID=minioadmin
S3_SECRET_ACCESS_KEY=minioadmin
S3_BUCKET_NAME=byos-ai

# Security (REQUIRED - generate a secure key)
SECRET_KEY=your-generated-secret-key  # Run: openssl rand -hex 32

# AI Providers (at least one required)
HUGGINGFACE_API_KEY=your_hf_token_here
SERPAPI_KEY=your_serpapi_key_here
```

## Start Your Services

### Step 1: Navigate to Docker Directory

```bash
cd backend/infra/docker
```

### Step 2: Start Core Services

```bash
docker compose up -d postgres redis minio
```

Wait for services to be healthy (about 10-30 seconds).

### Step 3: Start API Service

```bash
docker compose --profile api up -d
```

### Step 4: Start Worker Service

```bash
docker compose --profile worker up -d
```

Or start both together:

```bash
docker compose --profile api --profile worker up -d
```

## Verify Everything Works

### Check Services Status

```bash
docker compose ps
```

You should see:
- ✅ `byos_postgres` - healthy
- ✅ `byos_redis` - healthy  
- ✅ `byos_minio` - healthy
- ✅ `byos_api` - running
- ✅ `byos_worker` - running

### Test API

```bash
# Health check
curl http://localhost:8000/health

# API docs
open http://localhost:8000/api/v1/docs
```

### Check Logs

```bash
# API logs
docker compose logs -f api

# Worker logs
docker compose logs -f worker

# All logs
docker compose logs -f
```

## Using Multi-Region Setup

If you want to use the regions compose file:

```bash
docker compose -f docker-compose.yml -f docker-compose.regions.yml up -d
```

This will create:
- `api-us-east` on port 8001
- `api-eu-west` on port 8002
- `api-asia-pacific` on port 8003
- Plus corresponding workers

## Troubleshooting

### "Service 'api' not found"

**Fix:** Use profiles:
```bash
docker compose --profile api up -d
```

### "Missing environment variables"

**Fix:** Make sure `.env` file exists and has required variables:
```bash
cd backend
cp .env.example .env
# Edit .env with your values
```

### Port conflicts

**Fix:** Change ports in `docker-compose.yml` or stop conflicting services.

### Services won't start

**Fix:** Check logs:
```bash
docker compose logs
docker compose ps
```

## Next Steps

1. ✅ Base compose file created
2. ✅ Environment variables documented
3. ⏭️ Set up your `.env` file
4. ⏭️ Start services
5. ⏭️ Run database migrations: `docker exec -it byos_api alembic upgrade head`
6. ⏭️ Access MinIO console: http://localhost:9001 (create bucket `byos-ai`)

## Full Documentation

See `DOCKER_SETUP.md` for complete documentation.
