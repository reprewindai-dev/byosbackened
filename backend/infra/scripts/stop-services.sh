#!/bin/bash
# Stop services selectively

set -e

cd "$(dirname "$0")/../docker"

# Stop all services (profiles don't matter for stop)
docker compose down

echo "All services stopped"
