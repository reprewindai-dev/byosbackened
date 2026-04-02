#!/bin/bash

# Environment Variable Management Script
# Generates secure secrets and manages environment configuration

set -e

echo "🔐 Managing environment variables for Sovereign AI SaaS..."

# Function to generate secure random strings
generate_secret() {
    openssl rand -base64 64 | tr -d "=+/" | cut -c1-64
}

generate_password() {
    openssl rand -base64 32 | tr -d "=+/" | cut -c1-32
}

# Check if .env file exists
if [ ! -f ".env.production" ]; then
    echo "❌ .env.production file not found!"
    exit 1
fi

# Backup original file
cp .env.production .env.production.backup.$(date +%Y%m%d_%H%M%S)

echo "🔄 Generating secure environment variables..."

# Generate all secrets
SECRET_KEY=$(generate_secret)
AI_CITIZENSHIP_SECRET=$(generate_secret)
POSTGRES_PASSWORD=$(generate_password)
REDIS_PASSWORD=$(generate_password)
GRAFANA_PASSWORD=$(generate_password)
STRIPE_WEBHOOK_SECRET=$(generate_secret)

# Get current domain or use IP
if [ -n "$1" ]; then
    DOMAIN=$1
else
    DOMAIN=$(curl -s http://checkip.amazonaws.com).nip.io
fi

echo "🌐 Using domain: $DOMAIN"

# Update .env.production file
sed -i.tmp "s/your-super-secure-64-character-random-secret-key-here-change-this/$SECRET_KEY/g" .env.production
sed -i.tmp "s/your-ai-citizenship-secret-key-here-change-this/$AI_CITIZENSHIP_SECRET/g" .env.production
sed -i.tmp "s/your-secure-postgres-password-here/$POSTGRES_PASSWORD/g" .env.production
sed -i.tmp "s/your-secure-redis-password-here/$REDIS_PASSWORD/g" .env.production
sed -i.tmp "s/your-secure-grafana-password-here/$GRAFANA_PASSWORD/g" .env.production
sed -i.tmp "s/your-domain.com/$DOMAIN/g" .env.production

# Add additional secure variables
cat >> .env.production << EOF

# Additional Security Variables
STRIPE_WEBHOOK_SECRET=$STRIPE_WEBHOOK_SECRET
SESSION_SECRET=$(generate_secret)
CSRF_SECRET=$(generate_secret)
ENCRYPTION_KEY=$(generate_secret)

# LLM Configuration
MODEL_CACHE_DIR=/app/models
MAX_CONCURRENT_REQUESTS=10
MODEL_MAX_LENGTH=4096
GPU_MEMORY_FRACTION=0.8
CUDA_VISIBLE_DEVICES=0

# Performance Tuning
OMP_NUM_THREADS=4
TOKENIZERS_PARALLELISM=false

# Monitoring
SENTRY_DSN=your-sentry-dsn-here
LOG_LEVEL=INFO
LOG_FORMAT=json

# Backup Configuration
BACKUP_SCHEDULE=0 2 * * *
BACKUP_RETENTION_DAYS=30
BACKUP_ENCRYPTION_KEY=$(generate_secret)

# SSL Configuration
SSL_CERT_PATH=/app/infra/docker/ssl/cert.pem
SSL_KEY_PATH=/app/infra/docker/ssl/key.pem
EOF

# Clean up temp file
rm -f .env.production.tmp

echo "✅ Environment variables generated successfully!"
echo ""
echo "🔑 Generated secrets:"
echo "- SECRET_KEY: ${SECRET_KEY:0:16}..."
echo "- AI_CITIZENSHIP_SECRET: ${AI_CITIZENSHIP_SECRET:0:16}..."
echo "- POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:0:8}..."
echo "- REDIS_PASSWORD: ${REDIS_PASSWORD:0:8}..."
echo "- GRAFANA_PASSWORD: ${GRAFANA_PASSWORD:0:8}..."
echo ""
echo "⚠️  Please update the following variables manually:"
echo "- HUGGINGFACE_API_KEY"
echo "- OPENAI_API_KEY"
echo "- STRIPE_SECRET_KEY"
echo "- STRIPE_PUBLISHABLE_KEY"
echo "- SENTRY_DSN (if using Sentry)"
echo ""
echo "📋 Environment file updated: .env.production"
echo "💾 Backup created: .env.production.backup.$(date +%Y%m%d_%H%M%S)"

# Create .env.local for development
echo "📝 Creating .env.local for development..."
cat > .env.local << EOF
# Development Environment
ENVIRONMENT=development
DEBUG=true
SECRET_KEY=$SECRET_KEY
AI_CITIZENSHIP_SECRET=$AI_CITIZENSHIP_SECRET
DATABASE_URL=sqlite:///./local.db
REDIS_URL=redis://localhost:6379/0
FRONTEND_URL=http://localhost:3000
API_URL=http://localhost:8000
LOG_LEVEL=DEBUG
EOF

echo "✅ Development environment created: .env.local"
