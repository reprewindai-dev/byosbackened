#!/usr/bin/env bash
# Canary deployment script
# Usage: ./canary-deployment.sh [workspace_id] [enable|disable|monitor]

set -euo pipefail

WORKSPACE_ID=${1:-""}
ACTION=${2:-"monitor"}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$BACKEND_DIR"

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "Error: Docker not found"
    exit 1
fi

# Use docker compose (newer) or docker-compose (older)
if docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
else
    DOCKER_COMPOSE="docker-compose"
fi

DOCKER_DIR="$BACKEND_DIR/infra/docker"
cd "$DOCKER_DIR"

case "$ACTION" in
    enable)
        echo "Enabling canary deployment flags..."
        
        # Update environment variables
        if [ -f "$BACKEND_DIR/.env.staging" ]; then
            # Enable flags in .env.staging
            sed -i.bak 's/^CANARY_DEPLOYMENT_ENABLED=.*/CANARY_DEPLOYMENT_ENABLED=true/' "$BACKEND_DIR/.env.staging"
            sed -i.bak 's/^AUTONOMOUS_ROUTING_ENABLED=.*/AUTONOMOUS_ROUTING_ENABLED=true/' "$BACKEND_DIR/.env.staging"
            echo "Updated .env.staging"
        fi
        
        # Set environment variables for current session
        export CANARY_DEPLOYMENT_ENABLED=true
        export AUTONOMOUS_ROUTING_ENABLED=true
        
        # Restart API service
        echo "Restarting API service..."
        $DOCKER_COMPOSE restart api || docker restart byos_api
        
        sleep 5
        
        # Verify flags enabled
        echo ""
        echo "Verifying flags enabled..."
        docker exec -it byos_api python -c "
from core.autonomous.feature_flags import get_feature_flags
flags = get_feature_flags()
canary = flags.is_enabled('canary_deployment_enabled')
routing = flags.is_enabled('autonomous_routing_enabled')
print(f'Canary Deployment: {\"✅ ENABLED\" if canary else \"❌ DISABLED\"}')
print(f'Autonomous Routing: {\"✅ ENABLED\" if routing else \"❌ DISABLED\"}')
" || {
            echo "Error: Failed to verify flags"
            exit 1
        }
        
        echo ""
        echo "✅ Canary flags enabled"
        echo ""
        echo "Next steps:"
        echo "1. Monitor workspace: $WORKSPACE_ID"
        echo "2. Run: ./canary-deployment.sh $WORKSPACE_ID monitor"
        ;;
        
    disable)
        echo "Disabling canary deployment flags..."
        
        # Update environment variables
        if [ -f "$BACKEND_DIR/.env.staging" ]; then
            sed -i.bak 's/^CANARY_DEPLOYMENT_ENABLED=.*/CANARY_DEPLOYMENT_ENABLED=false/' "$BACKEND_DIR/.env.staging"
            sed -i.bak 's/^AUTONOMOUS_ROUTING_ENABLED=.*/AUTONOMOUS_ROUTING_ENABLED=false/' "$BACKEND_DIR/.env.staging"
            echo "Updated .env.staging"
        fi
        
        # Disable via runtime (faster)
        docker exec -it byos_api python -c "
from core.autonomous.feature_flags import get_feature_flags
flags = get_feature_flags()
flags.disable('canary_deployment_enabled')
flags.disable('autonomous_routing_enabled')
print('✅ Flags disabled via runtime')
" || {
            echo "Warning: Runtime disable failed, restarting service..."
            $DOCKER_COMPOSE restart api || docker restart byos_api
        }
        
        echo ""
        echo "✅ Canary flags disabled"
        ;;
        
    monitor)
        if [ -z "$WORKSPACE_ID" ]; then
            echo "Error: Workspace ID required for monitoring"
            echo "Usage: ./canary-deployment.sh <workspace_id> monitor"
            exit 1
        fi
        
        echo "Monitoring canary workspace: $WORKSPACE_ID"
        echo ""
        
        # Check cost
        echo "1. Cost Monitoring:"
        docker exec -it byos_api python -c "
from core.cost_intelligence.kill_switch import get_cost_kill_switch
from db.session import SessionLocal
from decimal import Decimal

db = SessionLocal()
kill_switch = get_cost_kill_switch()
result = kill_switch.check_workspace_cap(db, '$WORKSPACE_ID', Decimal('0'))
print(f'  Workspace spend: \${result[\"current_spend\"]} / \${result[\"cap\"]}')
print(f'  Remaining: \${result.get(\"remaining\", \"N/A\")}')
" || echo "  ⚠️  Failed to check cost"
        
        echo ""
        echo "2. Feature Flags Status:"
        docker exec -it byos_api python -c "
from core.autonomous.feature_flags import get_feature_flags
flags = get_feature_flags()
canary = flags.is_enabled('canary_deployment_enabled')
routing = flags.is_enabled('autonomous_routing_enabled')
print(f'  Canary Deployment: {\"✅\" if canary else \"❌\"}')
print(f'  Autonomous Routing: {\"✅\" if routing else \"❌\"}')
" || echo "  ⚠️  Failed to check flags"
        
        echo ""
        echo "3. Kill Switch Test:"
        echo "  Testing kill switch response time and behavioral change..."
        
        # Test 1: Response time
        START=$(date +%s.%N)
        docker exec -it byos_api python -c "
from core.autonomous.feature_flags import get_feature_flags
flags = get_feature_flags()
flags.disable('autonomous_routing_enabled')
" > /dev/null 2>&1
        END=$(date +%s.%N)
        RESPONSE_TIME=$(echo "$END - $START" | bc || echo "999")
        echo "  Response time: ${RESPONSE_TIME}s"
        
        # Test 2: Verify behavioral change (routing actually disabled)
        ROUTING_DISABLED=$(docker exec -it byos_api python -c "
from core.autonomous.feature_flags import get_feature_flags
flags = get_feature_flags()
print('true' if not flags.is_enabled('autonomous_routing_enabled') else 'false')
" 2>/dev/null || echo "false")
        
        if [ "$ROUTING_DISABLED" = "true" ]; then
            echo "  ✅ Behavioral change verified: routing disabled"
        else
            echo "  ❌ Behavioral change failed: routing still enabled"
        fi
        
        # Test 3: Verify cost kill switch (if applicable)
        COST_CHECK=$(docker exec -it byos_api python -c "
from core.cost_intelligence.kill_switch import get_cost_kill_switch
kill_switch = get_cost_kill_switch()
print('enabled' if kill_switch._enabled else 'disabled')
" 2>/dev/null || echo "unknown")
        echo "  Cost kill switch: $COST_CHECK"
        
        # Re-enable for monitoring
        docker exec -it byos_api python -c "
from core.autonomous.feature_flags import get_feature_flags
flags = get_feature_flags()
flags.enable('autonomous_routing_enabled')
" > /dev/null 2>&1
        
        # Check if bc is available for comparison
        if command -v bc &> /dev/null; then
            if (( $(echo "$RESPONSE_TIME < 1.0" | bc -l) )) && [ "$ROUTING_DISABLED" = "true" ]; then
                echo "  ✅ Kill switch test passed (< 1s response, behavioral change verified)"
            else
                echo "  ❌ Kill switch test failed"
                exit 1
            fi
        else
            echo "  ⚠️  bc not available, skipping time comparison"
            if [ "$ROUTING_DISABLED" = "true" ]; then
                echo "  ✅ Behavioral change verified"
            else
                echo "  ❌ Behavioral change failed"
                exit 1
            fi
        fi
        
        echo ""
        echo "4. Manual Checks Required:"
        echo "  - Check routing stats: curl http://localhost:8000/api/v1/autonomous/routing/stats?workspace_id=$WORKSPACE_ID"
        echo "  - Monitor Prometheus metrics: http://localhost:9090/metrics"
        echo "  - Check logs: docker logs -f byos_api | grep '$WORKSPACE_ID'"
        echo "  - Run tenant isolation test: pytest tests/test_tenant_isolation.py -v"
        echo "  - Trigger test alert and verify notification received"
        ;;
        
    *)
        echo "Usage: ./canary-deployment.sh [workspace_id] [enable|disable|monitor]"
        echo ""
        echo "Actions:"
        echo "  enable   - Enable canary deployment flags globally"
        echo "  disable  - Disable canary deployment flags"
        echo "  monitor  - Monitor canary workspace (requires workspace_id)"
        exit 1
        ;;
esac
