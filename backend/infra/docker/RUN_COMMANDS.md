# Docker Compose Run Commands

## Quick Start Commands

### 1. Validate Configuration
```bash
cd /srv/apps/byos_real/infra/docker
docker compose config
```
This validates the docker-compose.yml syntax without starting services.

### 2. Start Core Services (Postgres, Redis, MinIO)
```bash
docker compose up -d postgres redis minio
```

### 3. Start API Service
```bash
docker compose --profile api up -d
```

### 4. Start Worker Service
```bash
docker compose --profile worker up -d
```

### 5. Start All Services
```bash
docker compose --profile all up -d
```

## Verification Commands

### Check Service Status
```bash
docker compose ps
```

### View Logs
```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f api
docker compose logs -f worker
```

### Test API Health
```bash
curl http://localhost:8000/health
```

### Check Environment Variables
```bash
docker compose exec api env | grep -E "SECRET_KEY|ENCRYPTION_KEY|ALGORITHM"
docker compose exec worker env | grep -E "SECRET_KEY|ENCRYPTION_KEY|ALGORITHM"
```

## Rebuild After Changes

### Rebuild API
```bash
docker compose build --no-cache api
docker compose up -d api
```

### Rebuild Worker
```bash
docker compose build --no-cache worker
docker compose up -d worker
```

### Rebuild All
```bash
docker compose build --no-cache
docker compose up -d
```

## Stop Services

### Stop All
```bash
docker compose down
```

### Stop and Remove Volumes (⚠️ deletes data)
```bash
docker compose down -v
```

## Troubleshooting

### Check if SECRET_KEY is Set
```bash
docker compose exec api printenv SECRET_KEY
```

### Restart Service
```bash
docker compose restart api
docker compose restart worker
```
