#!/bin/bash

# Digital Ocean App Platform Deployment Script
# For serverless deployment without GPU

set -e

echo "🚀 Deploying Sovereign AI SaaS to Digital Ocean App Platform..."

# Check if doctl is installed
if ! command -v doctl &> /dev/null; then
    echo "❌ doctl is not installed. Please install it first:"
    echo "brew install doctl  # macOS"
    echo "or visit: https://github.com/digitalocean/doctl/releases"
    exit 1
fi

# Check if authenticated
if ! doctl account get &> /dev/null; then
    echo "❌ Not authenticated with Digital Ocean. Please run:"
    echo "doctl auth init"
    exit 1
fi

# Configuration
APP_NAME="sovereign-ai-saas"
REGION="nyc3"

# Create the app
echo "📦 Creating App Platform application..."
doctl apps create --spec .do/app.yaml

# Wait for deployment
echo "⏳ Waiting for deployment to complete..."
APP_ID=$(doctl apps list --format ID,Name | grep $APP_NAME | awk '{print $1}')

while true; do
    STATUS=$(doctl apps get $APP_ID --format Status | tail -n 1)
    echo "Current status: $STATUS"
    
    if [ "$STATUS" = "ACTIVE" ]; then
        break
    elif [ "$STATUS" = "ERROR" ]; then
        echo "❌ Deployment failed!"
        doctl apps get $APP_ID --format DegradedOn
        exit 1
    fi
    
    sleep 30
done

# Get app URL
APP_URL=$(doctl apps get $APP_ID --format DefaultIngress | tail -n 1)
echo "🎉 Deployment complete!"
echo "🌐 Application URL: $APP_URL"

# Set up environment variables
echo "📋 Setting up environment variables..."
doctl apps create-deployment $APP_ID --force-rebuild

echo ""
echo "📝 Next steps:"
echo "1. Update your custom domain if needed"
echo "2. Configure SSL (automatically handled by App Platform)"
echo "3. Set up monitoring alerts"
echo "4. Update your API keys in the App Platform dashboard"
