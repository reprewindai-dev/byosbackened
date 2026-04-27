#!/bin/bash
# Veklom Backend Deployment Script
# Usage: ./deploy_veklom.sh [staging|production]

set -e

ENVIRONMENT=${1:-staging}
VERSION=${2:-latest}
REGISTRY="ghcr.io/veklom"
IMAGE_NAME="backend"

echo "=========================================="
echo "Deploying Veklom Backend to ${ENVIRONMENT}"
echo "Version: ${VERSION}"
echo "=========================================="

# Check if we're in the right directory
if [ ! -f "docker-compose.prod.yml" ]; then
    echo "Error: Must run from backend directory with docker-compose.prod.yml"
    exit 1
fi

# Build the Docker image
echo "Building Docker image..."
docker build -f infra/docker/Dockerfile.api -t ${REGISTRY}/${IMAGE_NAME}:${VERSION} .
docker tag ${REGISTRY}/${IMAGE_NAME}:${VERSION} ${REGISTRY}/${IMAGE_NAME}:latest

# Push to registry (if credentials available)
if command -v docker &> /dev/null && docker info &> /dev/null; then
    echo "Pushing to registry..."
    docker push ${REGISTRY}/${IMAGE_NAME}:${VERSION}
    docker push ${REGISTRY}/${IMAGE_NAME}:latest
fi

# Deploy based on environment
if [ "$ENVIRONMENT" = "production" ]; then
    echo "Deploying to production..."
    
    # Use Coolify webhook or SSH deployment
    if [ -n "$COOLIFY_WEBHOOK_URL" ]; then
        echo "Triggering Coolify deployment..."
        curl -X POST "$COOLIFY_WEBHOOK_URL" \
            -H "Content-Type: application/json" \
            -d "{\"version\":\"${VERSION}\"}"
    else
        echo "Please deploy manually via Coolify dashboard or set COOLIFY_WEBHOOK_URL"
    fi
    
elif [ "$ENVIRONMENT" = "staging" ]; then
    echo "Deploying to staging with docker-compose..."
    
    # Create staging environment file
    cp .env.veklom.prod .env.staging
    
    # Update for staging values
    sed -i 's/ENVIRONMENT=production/ENVIRONMENT=staging/g' .env.staging
    sed -i 's/LOG_LEVEL=INFO/LOG_LEVEL=DEBUG/g' .env.staging
    
    # Deploy with docker-compose
    docker-compose -f docker-compose.prod.yml --env-file .env.staging down
    docker-compose -f docker-compose.prod.yml --env-file .env.staging pull
    docker-compose -f docker-compose.prod.yml --env-file .env.staging up -d
    
    # Run migrations
    echo "Running database migrations..."
    sleep 10  # Wait for DB to be ready
    docker-compose -f docker-compose.prod.yml --env-file .env.staging exec -T api alembic upgrade head
    
    echo "Staging deployment complete!"
    echo "API available at: http://localhost:8000"
fi

echo "=========================================="
echo "Deployment script completed"
echo "=========================================="
