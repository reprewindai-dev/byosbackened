#!/usr/bin/env bash
# Prepare staging environment variables file
# Usage: ./prepare-staging-env.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$BACKEND_DIR"

ENV_FILE=".env.staging"

# Check if .env.example exists
if [ ! -f .env.example ]; then
    echo "Warning: .env.example not found, creating from template"
fi

# Create staging env file from example if it doesn't exist
if [ ! -f "$ENV_FILE" ]; then
    if [ -f .env.example ]; then
        cp .env.example "$ENV_FILE"
        echo "Created $ENV_FILE from .env.example"
    else
        touch "$ENV_FILE"
        echo "Created empty $ENV_FILE"
    fi
fi

echo "Preparing staging environment file: $ENV_FILE"
echo ""
echo "Required variables to set:"
echo ""
echo "# Critical Secrets"
echo "SECRET_KEY=<generate with: openssl rand -hex 32>"
echo "DATABASE_URL=postgresql://user:pass@host:5432/byos_ai"
echo "REDIS_URL=redis://host:6379/0"
echo ""
echo "# Alert Channels (at least one required)"
echo "ALERT_EMAIL_TO=alerts@yourdomain.com"
echo "SMTP_HOST=smtp.yourdomain.com"
echo "SMTP_PORT=587"
echo "SMTP_USER=your-smtp-user"
echo "SMTP_PASS=your-smtp-password"
echo "# SLACK_WEBHOOK_URL=https://hooks.slack.com/services/..."
echo "# PAGERDUTY_INTEGRATION_KEY=pdk_..."
echo ""
echo "# Budget Caps (required)"
echo "GLOBAL_DAILY_COST_CAP=10000.00"
echo "DEFAULT_WORKSPACE_DAILY_CAP=1000.00"
echo "COST_KILL_SWITCH_ENABLED=true"
echo ""
echo "# Feature Flags (all default to false - must explicitly enable)"
echo "AUTONOMOUS_ROUTING_ENABLED=false"
echo "ML_COST_PREDICTION_ENABLED=false"
echo "ML_ROUTING_OPTIMIZER_ENABLED=false"
echo "MODEL_RETRAINING_ENABLED=false"
echo "CANARY_DEPLOYMENT_ENABLED=false"
echo "AUTO_REMEDIATION_ENABLED=false"
echo "EDGE_ROUTING_ENABLED=false"
echo "TRAFFIC_PREDICTION_ENABLED=false"
echo ""
echo "# Application"
echo "DEBUG=false"
echo "APP_NAME=BYOS AI Backend"
echo "APP_VERSION=$(git describe --tags 2>/dev/null || echo 'dev')"
echo ""
echo "Opening $ENV_FILE for editing..."
echo "Press Enter to continue..."
read

# Open editor (prefer $EDITOR, fallback to nano)
${EDITOR:-nano} "$ENV_FILE"

echo ""
echo "Staging environment file prepared: $ENV_FILE"
echo "Review and update all required variables before deployment."
