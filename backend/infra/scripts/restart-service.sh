#!/bin/bash
# Restart a single service by name

set -e

SERVICE=$1

if [ -z "$SERVICE" ]; then
    echo "Usage: $0 <service-name>"
    exit 1
fi

cd "$(dirname "$0")/../docker"

docker compose restart $SERVICE

echo "Service '$SERVICE' restarted"
