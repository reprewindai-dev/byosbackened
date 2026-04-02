#!/bin/bash
# Deploy to staging environment
# Usage: ./deploy-staging.sh [version_tag]

set -e

VERSION_TAG=${1:-$(git describe --tags --abbrev=0 2>/dev/null || echo "latest")}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
DOCKER_DIR="$BACKEND_DIR/infra/docker"

cd "$BACKEND_DIR"

# Check if .env.staging exists
if [ ! -f .env.staging ]; then
    echo "Error: .env.staging not found. Run prepare-staging-env.sh first"
    exit 1
fi

# Load staging environment variables
set -a
source .env.staging
set +a

echo "Deploying version: $VERSION_TAG"
echo "Environment: Staging"
echo ""

# Check if git repo and fetch latest
if [ -d .git ]; then
    echo "Fetching latest from git..."
    git fetch origin
    
    if [ "$VERSION_TAG" != "latest" ]; then
        echo "Checking out tag: $VERSION_TAG"
        git checkout "$VERSION_TAG"
    else
        echo "Using latest commit"
        git pull origin main || git pull origin master || true
    fi
fi

# Check Docker Compose
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "Error: docker-compose not found"
    exit 1
fi

# Use docker compose (newer) or docker-compose (older)
if docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
else
    DOCKER_COMPOSE="docker-compose"
fi

cd "$DOCKER_DIR"

echo ""
echo "Pulling latest images..."
$DOCKER_COMPOSE pull || true

echo ""
echo "Building and starting services..."
$DOCKER_COMPOSE up -d --build --force-recreate

echo ""
echo "Waiting for services to start..."
sleep 10

echo ""
echo "Running database migrations..."
MIGRATION_OUTPUT=$($DOCKER_COMPOSE exec -T api alembic upgrade head 2>&1)
MIGRATION_EXIT=$?

if [ $MIGRATION_EXIT -ne 0 ]; then
    echo "❌ Migration failed, aborting deployment"
    echo "$MIGRATION_OUTPUT"
    docker logs byos_api | tail -50
    exit 1
fi

echo "✅ Migrations completed successfully"

# Verify schema is at head
echo ""
echo "Verifying database schema is at head..."
HEAD_REV=$($DOCKER_COMPOSE exec -T api alembic heads 2>/dev/null | grep -oP '^\w+' | head -1 || echo "none")
CURRENT_REV=$($DOCKER_COMPOSE exec -T api alembic current 2>/dev/null | grep -oP '^\w+' || echo "none")

if [ "$CURRENT_REV" != "$HEAD_REV" ] && [ "$HEAD_REV" != "none" ]; then
    echo "❌ Schema not at head (current: $CURRENT_REV, head: $HEAD_REV)"
    exit 1
fi

echo "✅ Schema verified at head: $HEAD_REV"

echo ""
echo "Checking service status..."
$DOCKER_COMPOSE ps

echo ""
echo "Checking API health..."
sleep 5
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ API health check passed"
    curl http://localhost:8000/health
else
    echo "❌ API health check failed"
    echo "Checking logs..."
    docker logs byos_api | tail -50
    exit 1
fi

echo ""
echo "Checking startup validation..."
if docker logs byos_api 2>&1 | grep -q "Production configuration validated successfully"; then
    echo "✅ Startup validation passed"
else
    echo "⚠️  Startup validation message not found in logs"
    echo "Recent logs:"
    docker logs byos_api | tail -20
fi

echo ""
echo "✅ Deployment complete!"
echo ""
echo "Next steps:"
echo "1. Run verification tests: ./infra/scripts/run-verification-tests.sh"
echo "2. Monitor logs: docker logs -f byos_api"
echo "3. Check metrics: curl http://localhost:9090/metrics"
