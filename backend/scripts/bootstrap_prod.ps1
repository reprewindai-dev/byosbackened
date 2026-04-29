# bootstrap_prod.ps1 - Run ONCE from PowerShell to verify/wire Postgres + Redis into the live Veklom Coolify app.
# Usage: .\backend\scripts\bootstrap_prod.ps1
# Requirements: OpenSSH installed (built into Windows 10/11), SSH key at ~/.ssh/veklom-deploy

$VEKLOM_HOST = "5.78.135.11"
$SSH_KEY = "$env:USERPROFILE\.ssh\veklom-deploy"
$SSH_BASE = "ssh -F NUL -i `"$SSH_KEY`" -o StrictHostKeyChecking=no root@$VEKLOM_HOST"

Write-Host "=== Veklom Production Bootstrap ===" -ForegroundColor Cyan
Write-Host "Target: $VEKLOM_HOST"
Write-Host ""

# -- 1. List running containers --
Write-Host "[1/5] Listing running containers on $VEKLOM_HOST..." -ForegroundColor Yellow
Invoke-Expression "$SSH_BASE docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'"
Write-Host ""

# -- 2. Find Postgres --
Write-Host "[2/5] Detecting Postgres container..." -ForegroundColor Yellow
$PG_CONTAINER = Invoke-Expression "$SSH_BASE docker ps --format '{{.Names}}'" | Where-Object { $_ -match "postgres|postgresql|pg" } | Select-Object -First 1

if (-not $PG_CONTAINER) {
    Write-Host "  WARNING: No Postgres container found." -ForegroundColor Red
    Write-Host "  Go to Coolify -> Resources -> New Resource -> PostgreSQL, then re-run this script."
    $PG_URL = "NOT_FOUND"
} else {
    Write-Host "  FOUND: $PG_CONTAINER" -ForegroundColor Green
    $PG_ENV = Invoke-Expression "$SSH_BASE docker exec $PG_CONTAINER env"
    $PG_USER = ($PG_ENV | Where-Object { $_ -match "^POSTGRES_USER=" }) -replace "POSTGRES_USER=", ""
    $PG_PASS = ($PG_ENV | Where-Object { $_ -match "^POSTGRES_PASSWORD=" }) -replace "POSTGRES_PASSWORD=", ""
    $PG_DB   = ($PG_ENV | Where-Object { $_ -match "^POSTGRES_DB=" }) -replace "POSTGRES_DB=", ""
    if (-not $PG_USER) { $PG_USER = "postgres" }
    if (-not $PG_DB)   { $PG_DB = "postgres" }
    $PG_NETWORK = Invoke-Expression "$SSH_BASE docker inspect $PG_CONTAINER --format '{{range `$k,`$v := .NetworkSettings.Networks}}{{`$k}}{{end}}'" | Select-Object -First 1
    $PG_IP = Invoke-Expression "$SSH_BASE docker inspect $PG_CONTAINER --format '{{.NetworkSettings.Networks.$PG_NETWORK.IPAddress}}'"
    if (-not $PG_IP) { $PG_IP = "127.0.0.1" }
    $PG_URL = "postgresql://${PG_USER}:${PG_PASS}@${PG_IP}:5432/${PG_DB}"
    Write-Host "  DATABASE_URL=$PG_URL" -ForegroundColor Green
}
Write-Host ""

# -- 3. Find Redis --
Write-Host "[3/5] Detecting Redis container..." -ForegroundColor Yellow
$REDIS_CONTAINER = Invoke-Expression "$SSH_BASE docker ps --format '{{.Names}}'" | Where-Object { $_ -match "redis" } | Select-Object -First 1

if (-not $REDIS_CONTAINER) {
    Write-Host "  WARNING: No Redis container found." -ForegroundColor Red
    Write-Host "  Go to Coolify -> Resources -> New Resource -> Redis, then re-run this script."
    $REDIS_URL = "NOT_FOUND"
} else {
    Write-Host "  FOUND: $REDIS_CONTAINER" -ForegroundColor Green
    $REDIS_NETWORK = Invoke-Expression "$SSH_BASE docker inspect $REDIS_CONTAINER --format '{{range `$k,`$v := .NetworkSettings.Networks}}{{`$k}}{{end}}'" | Select-Object -First 1
    $REDIS_IP = Invoke-Expression "$SSH_BASE docker inspect $REDIS_CONTAINER --format '{{.NetworkSettings.Networks.$REDIS_NETWORK.IPAddress}}'"
    if (-not $REDIS_IP) { $REDIS_IP = "127.0.0.1" }
    $REDIS_PASS = Invoke-Expression "$SSH_BASE docker exec $REDIS_CONTAINER env" | Where-Object { $_ -match "REDIS_PASSWORD|requirepass" } | Select-Object -First 1
    $REDIS_PASS = $REDIS_PASS -replace ".*=", ""
    if ($REDIS_PASS) {
        $REDIS_URL = "redis://:${REDIS_PASS}@${REDIS_IP}:6379"
    } else {
        $REDIS_URL = "redis://${REDIS_IP}:6379"
    }
    Write-Host "  REDIS_URL=$REDIS_URL" -ForegroundColor Green
}
Write-Host ""

# -- 4. Check current env vars on veklom-api --
Write-Host "[4/5] Checking current env vars in veklom-api container..." -ForegroundColor Yellow
$API_CONTAINER = Invoke-Expression "$SSH_BASE docker ps --format '{{.Names}}'" | Where-Object { $_ -match "veklom-api|veklom_api" } | Select-Object -First 1

if (-not $API_CONTAINER) {
    Write-Host "  WARNING: veklom-api container not found. Is it running? Check Coolify." -ForegroundColor Red
} else {
    Write-Host "  Found API container: $API_CONTAINER" -ForegroundColor Green
    $API_ENV = Invoke-Expression "$SSH_BASE docker exec $API_CONTAINER env"
    $CURRENT_DB    = $API_ENV | Where-Object { $_ -match "^DATABASE_URL" }
    $CURRENT_REDIS = $API_ENV | Where-Object { $_ -match "^REDIS_URL" }
    if ($CURRENT_DB)    { Write-Host "  Current: $CURRENT_DB" -ForegroundColor Green }
    else                { Write-Host "  Current: DATABASE_URL=NOT SET" -ForegroundColor Red }
    if ($CURRENT_REDIS) { Write-Host "  Current: $CURRENT_REDIS" -ForegroundColor Green }
    else                { Write-Host "  Current: REDIS_URL=NOT SET" -ForegroundColor Red }
}
Write-Host ""

# -- 5. Print action --
Write-Host "[5/5] === ACTION REQUIRED ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "If DATABASE_URL or REDIS_URL are NOT SET above, go to Coolify and set them:"
Write-Host ""
Write-Host "  Coolify URL: http://$VEKLOM_HOST`:8000"
Write-Host "  App: veklom-api -> Environment Variables"
Write-Host ""
Write-Host "  Paste these exact values:" -ForegroundColor Yellow
Write-Host ""
Write-Host "  DATABASE_URL=$PG_URL" -ForegroundColor White
Write-Host "  REDIS_URL=$REDIS_URL" -ForegroundColor White
Write-Host ""
Write-Host "  Then click Save + Redeploy."
Write-Host ""
Write-Host "Smoke test after redeploy:"
Write-Host "  curl https://api.veklom.com/health"
Write-Host "  curl https://api.veklom.com/status"
Write-Host ""
Write-Host "=== Bootstrap complete ===" -ForegroundColor Cyan
