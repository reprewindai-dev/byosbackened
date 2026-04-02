# Docker Compose Setup Plan - Backend Deployment

## ✅ Issues Identified & Resolved

### Issue 1: Missing Base Docker Compose File ✅ FIXED

**Problem:** 
- Only had `docker-compose.regions.yml` which extends base services `api` and `worker`
- Base `docker-compose.yml` file was missing

**Solution:**
- ✅ Created `infra/docker/docker-compose.yml` with:
  - Core services: `postgres`, `redis`, `minio`
  - Application services: `api`, `worker`
  - Proper networking, volumes, and health checks
  - Environment variable support with defaults

### Issue 2: Missing Required Environment Variables ✅ DOCUMENTED

**Problem:**
- Docker Compose was warning about missing variables:
  - `DATABASE_URL`
  - `REDIS_URL`
  - `S3_ENDPOINT_URL`

**Solution:**
- ✅ Base compose file includes defaults for all three
- ✅ Created documentation explaining required vs optional variables
- ✅ `.env.example` already exists with all variables documented

## Files Created

1. **`infra/docker/docker-compose.yml`** - Base compose file
   - Core infrastructure (postgres, redis, minio)
   - API service (port 8000)
   - Worker service (Celery)
   - Profiles for modular deployment

2. **`infra/docker/DOCKER_SETUP.md`** - Complete setup guide
   - Service details
   - Environment variables reference
   - Common commands
   - Troubleshooting

3. **`infra/docker/QUICK_START_DOCKER.md`** - Quick start guide
   - Step-by-step instructions
   - Minimal setup for getting started
   - Verification steps

## Quick Start Steps

### 1. Set Up Environment Variables

```bash
cd backend
cp .env.example .env
```

Edit `.env` and set minimum required:

```bash
# Required - Generate with: openssl rand -hex 32
SECRET_KEY=your-generated-secret-key

# Required - Get from Hugging Face
HUGGINGFACE_API_KEY=your_hf_token_here

# Required - Get from SERP API
SERPAPI_KEY=your_serpapi_key_here
```

**Note:** `DATABASE_URL`, `REDIS_URL`, and `S3_ENDPOINT_URL` have defaults in docker-compose.yml that work for local Docker setup.

### 2. Start Services

```bash
cd infra/docker

# Start core services (postgres, redis, minio)
docker compose up -d postgres redis minio

# Start API and Worker
docker compose --profile api --profile worker up -d
```

### 3. Verify

```bash
# Check status
docker compose ps

# Check logs
docker compose logs -f api

# Test API
curl http://localhost:8000/health
```

## Environment Variables Reference

### Required (Minimum)

| Variable | Default (Docker) | Description |
|----------|------------------|-------------|
| `DATABASE_URL` | `postgresql://postgres:postgres@postgres:5432/byos_ai` | PostgreSQL connection |
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection |
| `S3_ENDPOINT_URL` | `http://minio:9000` | MinIO endpoint |
| `SECRET_KEY` | **None** | **Must set** - Generate with `openssl rand -hex 32` |
| `HUGGINGFACE_API_KEY` | **None** | **Must set** - Get from Hugging Face |
| `SERPAPI_KEY` | **None** | **Must set** - Get from SERP API |

### Optional (Have Defaults)

| Variable | Default | Description |
|----------|---------|-------------|
| `S3_ACCESS_KEY_ID` | `minioadmin` | MinIO access key |
| `S3_SECRET_ACCESS_KEY` | `minioadmin` | MinIO secret key |
| `S3_BUCKET_NAME` | `byos-ai` | S3 bucket name |
| `DEBUG` | `false` | Debug mode |
| `OPENAI_API_KEY` | (empty) | Optional OpenAI integration |

## Multi-Region Deployment

The `docker-compose.regions.yml` file now works correctly with the base compose file:

```bash
docker compose -f docker-compose.yml -f docker-compose.regions.yml up -d
```

This creates:
- `api-us-east` (port 8001)
- `api-eu-west` (port 8002)
- `api-asia-pacific` (port 8003)
- Corresponding workers for each region

## Service Architecture

```
┌─────────────────────────────────────────┐
│         Docker Compose Network          │
│                                         │
│  ┌──────────┐  ┌──────────┐          │
│  │ Postgres  │  │  Redis   │          │
│  │  :5432    │  │  :6379    │          │
│  └──────────┘  └──────────┘          │
│                                         │
│  ┌──────────┐                          │
│  │  MinIO   │                          │
│  │ :9000/01 │                          │
│  └──────────┘                          │
│                                         │
│  ┌──────────┐  ┌──────────┐          │
│  │   API    │  │  Worker  │          │
│  │  :8000   │  │ (Celery) │          │
│  └──────────┘  └──────────┘          │
└─────────────────────────────────────────┘
```

## Next Steps for Server Deployment

1. ✅ Base compose file created
2. ✅ Environment variables documented
3. ⏭️ Copy files to your server
4. ⏭️ Set up `.env` file on server with production values
5. ⏭️ Update `DATABASE_URL`, `REDIS_URL`, `S3_ENDPOINT_URL` for your server infrastructure
6. ⏭️ Start services: `docker compose --profile api --profile worker up -d`
7. ⏭️ Run migrations: `docker exec -it byos_api alembic upgrade head`
8. ⏭️ Configure MinIO bucket (access console at http://your-server:9001)

## Documentation Files

- **`infra/docker/DOCKER_SETUP.md`** - Complete reference guide
- **`infra/docker/QUICK_START_DOCKER.md`** - Quick start instructions
- **`.env.example`** - All environment variables with examples

## Verification Checklist

- [x] Base `docker-compose.yml` created with `api` and `worker` services
- [x] Core services (`postgres`, `redis`, `minio`) configured
- [x] Environment variables documented with defaults
- [x] Regions compose file verified to work with base
- [x] Setup documentation created
- [ ] `.env` file created on server
- [ ] Services started and verified
- [ ] Database migrations run
- [ ] MinIO bucket created

## Support

If you encounter issues:

1. Check logs: `docker compose logs -f`
2. Verify environment: `docker compose config`
3. Check service health: `docker compose ps`
4. Review `DOCKER_SETUP.md` for troubleshooting
