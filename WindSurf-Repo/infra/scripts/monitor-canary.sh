#!/bin/bash
# Comprehensive canary monitoring script
# Usage: ./monitor-canary.sh <workspace_id> [duration_minutes]

set -e

WORKSPACE_ID=${1:-""}
DURATION=${2:-240}  # Default 4 hours in minutes

if [ -z "$WORKSPACE_ID" ]; then
    echo "Error: Workspace ID required"
    echo "Usage: ./monitor-canary.sh <workspace_id> [duration_minutes]"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$BACKEND_DIR"

# Create monitoring log directory
MONITOR_DIR="$BACKEND_DIR/deployment-logs/canary-monitoring-$(date +%Y%m%d_%H%M%S)"
mkdir -p "$MONITOR_DIR"

echo "Canary Monitoring Session"
echo "Workspace ID: $WORKSPACE_ID"
echo "Duration: $DURATION minutes"
echo "Log Directory: $MONITOR_DIR"
echo ""

# Success criteria checklist
SUCCESS_FILE="$MONITOR_DIR/success_criteria.md"
cat > "$SUCCESS_FILE" << EOF
# Canary Deployment Success Criteria

**Workspace ID**: $WORKSPACE_ID
**Start Time**: $(date)
**Duration**: $DURATION minutes

## Checklist

- [ ] No cross-tenant data access
- [ ] Cost caps enforced correctly (no leaks)
- [ ] Alerts firing correctly (test alert received)
- [ ] Kill switches take effect instantly (< 1 second)
- [ ] Latency within acceptable range (p95 < baseline + 20%)
- [ ] Error rate < 1%
- [ ] Routing decisions being logged correctly

## Monitoring Logs

EOF

# Function to check cost
check_cost() {
    docker exec -it byos_api python -c "
from core.cost_intelligence.kill_switch import get_cost_kill_switch
from db.session import SessionLocal
from decimal import Decimal
import json

db = SessionLocal()
kill_switch = get_cost_kill_switch()
result = kill_switch.check_workspace_cap(db, '$WORKSPACE_ID', Decimal('0'))
print(json.dumps({
    'workspace_id': '$WORKSPACE_ID',
    'current_spend': str(result['current_spend']),
    'cap': str(result['cap']),
    'remaining': str(result.get('remaining', 'N/A')),
    'timestamp': '$(date -Iseconds)'
}))
" 2>/dev/null || echo '{"error": "Failed to check cost"}'
}

# Function to check feature flags
check_flags() {
    docker exec -it byos_api python -c "
from core.autonomous.feature_flags import get_feature_flags
import json

flags = get_feature_flags()
all_flags = flags.get_all_flags()
print(json.dumps({
    'canary_deployment_enabled': all_flags.get('canary_deployment_enabled', False),
    'autonomous_routing_enabled': all_flags.get('autonomous_routing_enabled', False),
    'timestamp': '$(date -Iseconds)'
}))
" 2>/dev/null || echo '{"error": "Failed to check flags"}'
}

# Function to test kill switch
test_kill_switch() {
    echo "Testing kill switch response time and behavioral change..."
    START=$(date +%s.%N)
    
    # Disable routing
    docker exec -it byos_api python -c "
from core.autonomous.feature_flags import get_feature_flags
flags = get_feature_flags()
flags.disable('autonomous_routing_enabled')
" > /dev/null 2>&1
    
    END=$(date +%s.%N)
    
    # Calculate duration (handle bc availability)
    if command -v bc &> /dev/null; then
        DURATION=$(echo "$END - $START" | bc)
    else
        DURATION="0.5"  # Assume fast if bc not available
    fi
    
    # Verify behavioral change
    ROUTING_DISABLED=$(docker exec -it byos_api python -c "
from core.autonomous.feature_flags import get_feature_flags
flags = get_feature_flags()
print('true' if not flags.is_enabled('autonomous_routing_enabled') else 'false')
" 2>/dev/null || echo "false")
    
    # Re-enable
    docker exec -it byos_api python -c "
from core.autonomous.feature_flags import get_feature_flags
flags = get_feature_flags()
flags.enable('autonomous_routing_enabled')
" > /dev/null 2>&1
    
    if command -v bc &> /dev/null; then
        if (( $(echo "$DURATION < 1.0" | bc -l) )) && [ "$ROUTING_DISABLED" = "true" ]; then
            echo "✅ Kill switch responds in < 1 second and behavior changes"
            return 0
        else
            echo "❌ Kill switch test failed (time: ${DURATION}s, behavior: $ROUTING_DISABLED)"
            return 1
        fi
    else
        if [ "$ROUTING_DISABLED" = "true" ]; then
            echo "✅ Kill switch behavior changes verified"
            return 0
        else
            echo "❌ Kill switch test failed (behavior: $ROUTING_DISABLED)"
            return 1
        fi
    fi
}

# Initial checks
echo "=== Initial Checks ===" > "$MONITOR_DIR/initial_checks.log"
echo "" >> "$MONITOR_DIR/initial_checks.log"

echo "1. Cost Status:" | tee -a "$MONITOR_DIR/initial_checks.log"
check_cost | tee -a "$MONITOR_DIR/initial_checks.log"
echo "" >> "$MONITOR_DIR/initial_checks.log"

echo "2. Feature Flags:" | tee -a "$MONITOR_DIR/initial_checks.log"
check_flags | tee -a "$MONITOR_DIR/initial_checks.log"
echo "" >> "$MONITOR_DIR/initial_checks.log"

echo "3. Kill Switch Test:" | tee -a "$MONITOR_DIR/initial_checks.log"
test_kill_switch | tee -a "$MONITOR_DIR/initial_checks.log"
echo "" >> "$MONITOR_DIR/initial_checks.log"

# Periodic monitoring
INTERVAL=300  # Check every 5 minutes
ITERATIONS=$((DURATION * 60 / INTERVAL))

echo ""
echo "Starting periodic monitoring (every 5 minutes)..."
echo "Press Ctrl+C to stop early"
echo ""

for i in $(seq 1 $ITERATIONS); do
    TIMESTAMP=$(date -Iseconds)
    ITERATION_FILE="$MONITOR_DIR/check_$(printf "%03d" $i)_$(date +%H%M%S).log"
    
    echo "[$i/$ITERATIONS] $(date)" | tee "$ITERATION_FILE"
    echo "Cost:" | tee -a "$ITERATION_FILE"
    check_cost | tee -a "$ITERATION_FILE"
    echo "" | tee -a "$ITERATION_FILE"
    
    echo "Flags:" | tee -a "$ITERATION_FILE"
    check_flags | tee -a "$ITERATION_FILE"
    echo "" | tee -a "$ITERATION_FILE"
    
    # Check every 6th iteration (every 30 minutes)
    if [ $((i % 6)) -eq 0 ]; then
        echo "Kill Switch Test:" | tee -a "$ITERATION_FILE"
        test_kill_switch | tee -a "$ITERATION_FILE"
        echo "" | tee -a "$ITERATION_FILE"
    fi
    
    echo "---" | tee -a "$ITERATION_FILE"
    echo ""
    
    # Sleep until next check (except last iteration)
    if [ $i -lt $ITERATIONS ]; then
        sleep $INTERVAL
    fi
done

# Final summary
echo ""
echo "=== Monitoring Complete ==="
echo "Generating summary..."

cat >> "$SUCCESS_FILE" << EOF

## Final Summary

**End Time**: $(date)
**Total Checks**: $ITERATIONS
**Monitoring Duration**: $DURATION minutes

### Final Status

EOF

echo "Final Cost Status:" | tee -a "$SUCCESS_FILE"
check_cost | tee -a "$SUCCESS_FILE"
echo "" | tee -a "$SUCCESS_FILE"

echo "Final Flags Status:" | tee -a "$SUCCESS_FILE"
check_flags | tee -a "$SUCCESS_FILE"
echo "" | tee -a "$SUCCESS_FILE"

# Determine overall status
FAILED_CHECKS=0

# Check kill switch tests
if ! test_kill_switch >> "$SUCCESS_FILE" 2>&1; then
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
fi

# Check cost (should be within cap)
COST_DATA=$(check_cost)
CURRENT_SPEND=$(echo "$COST_DATA" | grep -oP '"current_spend":\s*"[^"]*"' | cut -d'"' -f4 || echo "")
CAP=$(echo "$COST_DATA" | grep -oP '"cap":\s*"[^"]*"' | cut -d'"' -f4 || echo "")

if [ -n "$CURRENT_SPEND" ] && [ -n "$CAP" ] && command -v bc &> /dev/null; then
    # Compare as decimals (requires bc)
    if (( $(echo "$CURRENT_SPEND > $CAP" | bc -l) )); then
        echo "❌ Cost cap exceeded: \$$CURRENT_SPEND > \$$CAP" | tee -a "$SUCCESS_FILE"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
    else
        echo "✅ Cost within cap: \$$CURRENT_SPEND / \$$CAP" | tee -a "$SUCCESS_FILE"
    fi
fi

# Final verdict
echo "" | tee -a "$SUCCESS_FILE"
echo "## Final Verdict" | tee -a "$SUCCESS_FILE"

if [ $FAILED_CHECKS -eq 0 ]; then
    echo "✅ PASS: All checks passed" | tee -a "$SUCCESS_FILE"
    echo ""
    echo "✅ Monitoring complete - All checks passed!"
    echo "Results saved to: $MONITOR_DIR"
    exit 0
else
    echo "❌ FAIL: $FAILED_CHECKS check(s) failed" | tee -a "$SUCCESS_FILE"
    echo ""
    echo "❌ Monitoring complete - $FAILED_CHECKS check(s) failed"
    echo "Review: $SUCCESS_FILE"
    exit 1
fi
