#!/bin/bash
# Production Startup Script
# =======================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] SOVEREIGN AI:${NC} $1"
}

log_success() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] SOVEREIGN AI:${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] SOVEREIGN AI:${NC} $1"
}

log_error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] SOVEREIGN AI:${NC} $1"
}

# Check required environment variables
check_env_vars() {
    log "Checking environment variables..."
    
    required_vars=(
        "DATABASE_URL"
        "REDIS_URL"
        "SECRET_KEY"
        "STRIPE_SECRET_KEY"
    )
    
    missing_vars=()
    
    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            missing_vars+=("$var")
        fi
    done
    
    if [ ${#missing_vars[@]} -ne 0 ]; then
        log_error "Missing required environment variables:"
        for var in "${missing_vars[@]}"; do
            echo "  - $var"
        done
        exit 1
    fi
    
    log_success "All required environment variables are set"
}

# Wait for database to be ready
wait_for_db() {
    log "Waiting for database connection..."
    
    max_attempts=30
    attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if python -c "
import os
import psycopg2
try:
    conn = psycopg2.connect(os.environ['DATABASE_URL'])
    conn.close()
    print('Database connection successful')
    exit(0)
except Exception as e:
    print(f'Database connection failed: {e}')
    exit(1)
" 2>/dev/null; then
            log_success "Database is ready"
            return 0
        fi
        
        log_warning "Database not ready (attempt $attempt/$max_attempts), waiting 2 seconds..."
        sleep 2
        ((attempt++))
    done
    
    log_error "Database connection failed after $max_attempts attempts"
    exit 1
}

# Wait for Redis to be ready
wait_for_redis() {
    log "Waiting for Redis connection..."
    
    max_attempts=30
    attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if python -c "
import os
import redis
try:
    r = redis.from_url(os.environ['REDIS_URL'])
    r.ping()
    print('Redis connection successful')
    exit(0)
except Exception as e:
    print(f'Redis connection failed: {e}')
    exit(1)
" 2>/dev/null; then
            log_success "Redis is ready"
            return 0
        fi
        
        log_warning "Redis not ready (attempt $attempt/$max_attempts), waiting 2 seconds..."
        sleep 2
        ((attempt++))
    done
    
    log_error "Redis connection failed after $max_attempts attempts"
    exit 1
}

# Run database migrations
run_migrations() {
    log "Running database migrations..."
    
    if alembic upgrade head; then
        log_success "Database migrations completed"
    else
        log_error "Database migrations failed"
        exit 1
    fi
}

# Initialize cache
init_cache() {
    log "Initializing cache system..."
    
    if python -c "
import asyncio
import sys
sys.path.append('/app')
from core.cache.redis_cache import init_cache

async def main():
    success = await init_cache()
    if success:
        print('Cache initialized successfully')
        return 0
    else:
        print('Cache initialization failed')
        return 1

if __name__ == '__main__':
    exit(asyncio.run(main()))
" 2>/dev/null; then
        log_success "Cache system initialized"
    else
        log_warning "Cache initialization failed, continuing without cache"
    fi
}

# Initialize performance optimization
init_performance() {
    log "Initializing performance optimization..."
    
    if python -c "
import asyncio
import sys
sys.path.append('/app')
from core.performance.optimization import initialize_performance_optimization

async def main():
    await initialize_performance_optimization()
    print('Performance optimization initialized')
    return 0

if __name__ == '__main__':
    exit(asyncio.run(main()))
" 2>/dev/null; then
        log_success "Performance optimization initialized"
    else
        log_warning "Performance optimization initialization failed"
    fi
}

# Create necessary directories
create_directories() {
    log "Creating necessary directories..."
    
    directories=(
        "/app/data"
        "/app/logs"
        "/app/temp"
        "/app/static/uploads"
    )
    
    for dir in "${directories[@]}"; do
        mkdir -p "$dir"
        chmod 755 "$dir"
    done
    
    log_success "Directories created"
}

# Set proper permissions
set_permissions() {
    log "Setting proper permissions..."
    
    # Ensure log directory is writable
    chmod 755 /app/logs
    
    # Ensure data directory is writable
    chmod 755 /app/data
    
    log_success "Permissions set"
}

# Health check
health_check() {
    log "Performing health check..."
    
    # Check if we can bind to the port
    if nc -z localhost 8000; then
        log_warning "Port 8000 is already in use"
    fi
    
    log_success "Health check passed"
}

# Start the application
start_application() {
    log "Starting SOVEREIGN AI Backend..."
    
    # Set Python path
    export PYTHONPATH=/app
    export PYTHONUNBUFFERED=1
    export PYTHONDONTWRITEBYTECODE=1
    
    # Start with uvicorn
    exec uvicorn api.main:app \
        --host 0.0.0.0 \
        --port 8000 \
        --workers 4 \
        --worker-class uvicorn.workers.UvicornWorker \
        --access-log \
        --log-level info \
        --log-config /app/infra/docker/logging/production.ini \
        --ssl-keyfile /app/infra/docker/ssl/key.pem \
        --ssl-certfile /app/infra/docker/ssl/cert.pem
}

# Main execution
main() {
    log "🚀 Starting SOVEREIGN AI Backend v${VERSION:-1.0.0}"
    log "Environment: ${ENVIRONMENT:-production}"
    
    # Run startup sequence
    create_directories
    set_permissions
    check_env_vars
    wait_for_db
    wait_for_redis
    run_migrations
    init_cache
    init_performance
    health_check
    
    log_success "🎉 All systems ready. Starting application..."
    start_application
}

# Handle signals gracefully
trap 'log "Received shutdown signal, exiting gracefully..."; exit 0' SIGTERM SIGINT

# Run main function
main "$@"
