#!/usr/bin/env bash
# bootstrap_prod.sh — Run ONCE from your local machine to verify/wire Postgres + Redis into the live Veklom Coolify app.
# Usage: bash backend/scripts/bootstrap_prod.sh
# Requirements: ssh key at ~/.ssh/veklom-deploy, curl, jq

set -euo pipefail

VEKLOM_HOST="5.78.135.11"
SSH_KEY="$HOME/.ssh/veklom-deploy"
SSH_CMD="ssh -F /dev/null -i $SSH_KEY -o StrictHostKeyChecking=no root@$VEKLOM_HOST"

echo "=== Veklom Production Bootstrap ==="
echo "Target: $VEKLOM_HOST"
echo ""

# ── 1. Check what containers are running ──────────────────────────────────────
echo "[1/5] Listing running containers on $VEKLOM_HOST..."
$SSH_CMD docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'
echo ""

# ── 2. Find Postgres container and extract connection string ──────────────────
echo "[2/5] Detecting Postgres container..."
PG_CONTAINER=$($SSH_CMD docker ps --format '{{.Names}}' | grep -i 'postgres\|postgresql\|pg' | head -1 || true)

if [ -z "$PG_CONTAINER" ]; then
  echo "  ⚠️  No Postgres container found. You need to create one in Coolify:"
  echo "     Coolify dashboard → Resources → New Resource → PostgreSQL"
  echo "     Then re-run this script."
  PG_URL="NOT_FOUND"
else
  echo "  ✅ Found Postgres container: $PG_CONTAINER"
  PG_USER=$($SSH_CMD docker exec $PG_CONTAINER env | grep POSTGRES_USER | cut -d= -f2 || echo "postgres")
  PG_PASS=$($SSH_CMD docker exec $PG_CONTAINER env | grep POSTGRES_PASSWORD | cut -d= -f2 || echo "")
  PG_DB=$($SSH_CMD docker exec $PG_CONTAINER env | grep POSTGRES_DB | cut -d= -f2 || echo "postgres")
  PG_NETWORK=$($SSH_CMD docker inspect $PG_CONTAINER --format '{{range $k,$v := .NetworkSettings.Networks}}{{$k}}{{end}}' | head -1)
  PG_IP=$($SSH_CMD docker inspect $PG_CONTAINER --format "{{.NetworkSettings.Networks.$PG_NETWORK.IPAddress}}" 2>/dev/null || echo "127.0.0.1")
  PG_URL="postgresql://${PG_USER}:${PG_PASS}@${PG_IP}:5432/${PG_DB}"
  echo "  DATABASE_URL=$PG_URL"
fi
echo ""

# ── 3. Find Redis container and extract connection string ─────────────────────
echo "[3/5] Detecting Redis container..."
REDIS_CONTAINER=$($SSH_CMD docker ps --format '{{.Names}}' | grep -i 'redis' | head -1 || true)

if [ -z "$REDIS_CONTAINER" ]; then
  echo "  ⚠️  No Redis container found. You need to create one in Coolify:"
  echo "     Coolify dashboard → Resources → New Resource → Redis"
  echo "     Then re-run this script."
  REDIS_URL="NOT_FOUND"
else
  echo "  ✅ Found Redis container: $REDIS_CONTAINER"
  REDIS_NETWORK=$($SSH_CMD docker inspect $REDIS_CONTAINER --format '{{range $k,$v := .NetworkSettings.Networks}}{{$k}}{{end}}' | head -1)
  REDIS_IP=$($SSH_CMD docker inspect $REDIS_CONTAINER --format "{{.NetworkSettings.Networks.$REDIS_NETWORK.IPAddress}}" 2>/dev/null || echo "127.0.0.1")
  REDIS_PASS=$($SSH_CMD docker exec $REDIS_CONTAINER env 2>/dev/null | grep -i 'redis_password\|requirepass' | cut -d= -f2 || echo "")
  if [ -z "$REDIS_PASS" ]; then
    REDIS_URL="redis://${REDIS_IP}:6379"
  else
    REDIS_URL="redis://:${REDIS_PASS}@${REDIS_IP}:6379"
  fi
  echo "  REDIS_URL=$REDIS_URL"
fi
echo ""

# ── 4. Check current env vars on the veklom-api container ────────────────────
echo "[4/5] Checking current DATABASE_URL + REDIS_URL in veklom-api container..."
API_CONTAINER=$($SSH_CMD docker ps --format '{{.Names}}' | grep -i 'veklom-api\|veklom_api' | head -1 || true)

if [ -z "$API_CONTAINER" ]; then
  echo "  ⚠️  veklom-api container not found. Is it running? Check Coolify dashboard."
else
  echo "  Found API container: $API_CONTAINER"
  CURRENT_DB=$($SSH_CMD docker exec $API_CONTAINER env 2>/dev/null | grep DATABASE_URL || echo "  DATABASE_URL=NOT SET")
  CURRENT_REDIS=$($SSH_CMD docker exec $API_CONTAINER env 2>/dev/null | grep REDIS_URL || echo "  REDIS_URL=NOT SET")
  echo "  Current: $CURRENT_DB"
  echo "  Current: $CURRENT_REDIS"
fi
echo ""

# ── 5. Print the exact action needed ─────────────────────────────────────────
echo "[5/5] === ACTION REQUIRED ==="
echo ""
echo "If DATABASE_URL or REDIS_URL are NOT SET above, go to Coolify and set them:"
echo ""
echo "  Coolify URL: http://$VEKLOM_HOST:8000"
echo "  App: veklom-api → Environment Variables"
echo ""
echo "  Paste these exact values:"
echo ""
echo "  DATABASE_URL=$PG_URL"
echo "  REDIS_URL=$REDIS_URL"
echo ""
echo "  Then click Save + Redeploy."
echo ""
echo "If both are already set correctly, run the smoke test:"
echo "  curl https://api.veklom.com/health"
echo "  curl https://api.veklom.com/status"
echo ""
echo "=== Bootstrap complete ==="
