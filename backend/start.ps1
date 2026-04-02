# BYOS AI Backend — Local Windows Quick Start
# Run from the backend/ directory:  .\start.ps1
#
# What this does:
#   1. Verifies Ollama is running and qwen2.5:3b is available
#   2. Runs DB migrations (inside a temp container)
#   3. Brings up the dev stack (postgres, redis, minio, api)
#   4. Tails logs until Ctrl+C

param(
    [switch]$SkipOllamaCheck,
    [switch]$NoBuild,
    [switch]$Down
)

$ErrorActionPreference = "Stop"
$ComposeFile = "docker-compose.dev.yml"

if ($Down) {
    Write-Host "[byos] Stopping dev stack..." -ForegroundColor Yellow
    docker compose -f $ComposeFile down
    exit 0
}

# ── 1. Verify Ollama ────────────────────────────────────────────────────────

if (-not $SkipOllamaCheck) {
    Write-Host "[byos] Checking Ollama..." -ForegroundColor Cyan
    try {
        $tags = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 3
        $models = $tags.models | ForEach-Object { $_.name }
        if ("qwen2.5:3b" -notin $models) {
            Write-Host "[byos] Pulling qwen2.5:3b (best model for CPU-only / 16GB RAM)..." -ForegroundColor Yellow
            ollama pull qwen2.5:3b
        } else {
            Write-Host "[byos] Ollama OK — qwen2.5:3b available" -ForegroundColor Green
        }
    } catch {
        Write-Host "[byos] ERROR: Ollama is not running at http://127.0.0.1:11434" -ForegroundColor Red
        Write-Host "       Start Ollama: run 'ollama serve' in another terminal" -ForegroundColor Red
        exit 1
    }
}

# ── 2. Build (unless skipped) ───────────────────────────────────────────────

if (-not $NoBuild) {
    Write-Host "[byos] Building images..." -ForegroundColor Cyan
    docker compose -f $ComposeFile build --quiet
}

# ── 3. Start infrastructure only first ─────────────────────────────────────

Write-Host "[byos] Starting postgres + redis + minio..." -ForegroundColor Cyan
docker compose -f $ComposeFile up -d postgres redis minio

Write-Host "[byos] Waiting for postgres to be ready..." -ForegroundColor Cyan
$retries = 0
do {
    Start-Sleep -Seconds 2
    $retries++
    $health = docker inspect --format='{{.State.Health.Status}}' byos_dev_postgres 2>$null
} while ($health -ne "healthy" -and $retries -lt 20)

if ($health -ne "healthy") {
    Write-Host "[byos] ERROR: Postgres did not become healthy in time." -ForegroundColor Red
    exit 1
}

# ── 4. Run migrations ───────────────────────────────────────────────────────

Write-Host "[byos] Running Alembic migrations..." -ForegroundColor Cyan
docker compose -f $ComposeFile run --rm --no-deps api `
    alembic upgrade head

# ── 5. Seed dev API key (idempotent — skips if already exists) ──────────────

Write-Host "[byos] Seeding dev API key..." -ForegroundColor Cyan
docker compose -f $ComposeFile run --rm --no-deps api `
    python scripts/seed_dev_apikey.py

# ── 6. Start full stack ─────────────────────────────────────────────────────

Write-Host "[byos] Starting API service..." -ForegroundColor Cyan
docker compose -f $ComposeFile up -d

# ── 7. Health check ─────────────────────────────────────────────────────────

Write-Host "[byos] Waiting for API to be ready..." -ForegroundColor Cyan
$retries = 0
do {
    Start-Sleep -Seconds 2
    $retries++
    try {
        $health = Invoke-RestMethod -Uri "http://localhost:8000/health" -TimeoutSec 2
    } catch {
        $health = $null
    }
} while ($health -eq $null -and $retries -lt 20)

# ── 7. Verify endpoints ─────────────────────────────────────────────────────

Write-Host ""
Write-Host "─────────────────────────────────────────" -ForegroundColor DarkGray
Write-Host " BYOS AI Backend — Dev Stack Running" -ForegroundColor Green
Write-Host "─────────────────────────────────────────" -ForegroundColor DarkGray
Write-Host " API:      http://localhost:8000"
Write-Host " Docs:     http://localhost:8000/api/v1/docs"
Write-Host " Status:   http://localhost:8000/status"
Write-Host " MinIO:    http://localhost:9001"
Write-Host "─────────────────────────────────────────" -ForegroundColor DarkGray
Write-Host ""

try {
    $status = Invoke-RestMethod -Uri "http://localhost:8000/status" -TimeoutSec 5
    Write-Host " db_ok:    $($status.db_ok)" -ForegroundColor $(if ($status.db_ok) { "Green" } else { "Red" })
    Write-Host " redis_ok: $($status.redis_ok)" -ForegroundColor $(if ($status.redis_ok) { "Green" } else { "Red" })
    Write-Host " llm_ok:   $($status.llm_ok)" -ForegroundColor $(if ($status.llm_ok) { "Green" } else { "Red" })
    if ($status.llm_models_available) {
        Write-Host " models:   $($status.llm_models_available -join ', ')"
    }
} catch {
    Write-Host " [status endpoint not yet ready — check logs]" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "[byos] Tailing logs (Ctrl+C to stop)..." -ForegroundColor Cyan
docker compose -f $ComposeFile logs -f api
