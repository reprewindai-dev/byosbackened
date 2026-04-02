#!/bin/bash
# Run verification tests and save outputs
# Usage: ./run-verification-tests.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$BACKEND_DIR"

# Create log directory
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_DIR="$BACKEND_DIR/deployment-logs/$TIMESTAMP"
mkdir -p "$LOG_DIR"

echo "Running verification tests..."
echo "Log directory: $LOG_DIR"
echo ""

# Check if running in Docker or locally
if [ -f /.dockerenv ] || [ -n "$DOCKER_CONTAINER" ]; then
    PYTHON_CMD="python"
    DOCKER_PREFIX=""
else
    PYTHON_CMD="python"
    # Check if we need to run via docker
    if command -v docker &> /dev/null; then
        if docker ps | grep -q byos_api; then
            DOCKER_PREFIX="docker exec -it byos_api"
        fi
    fi
fi

# Function to run test and save output
run_test() {
    local test_num=$1
    local test_name=$2
    local test_cmd=$3
    local log_file="$LOG_DIR/${test_num}_${test_name}.log"
    
    echo "[$test_num] Running: $test_name"
    eval "$test_cmd" > "$log_file" 2>&1 || {
        echo "  ⚠️  Test failed (check $log_file)"
        return 1
    }
    echo "  ✅ Test passed"
    return 0
}

# Test 1: Final checklist
run_test "01" "final_checklist" \
    "pytest tests/qa/final_checklist.py -v" || true

# Test 2: Tenant isolation
run_test "02" "tenant_isolation" \
    "pytest tests/test_tenant_isolation.py -v" || true

# Test 3: Migration reversibility
run_test "03" "migration_reversibility" \
    "pytest tests/test_migrations.py -v" || true

# Test 4: Alert routing
run_test "04" "alert_routing" \
    "pytest tests/alerts/test_alert_routing.py -v -s" || true

# Test 5: Backup/restore smoke test
run_test "05" "backup_restore" \
    "pytest tests/backup/test_restore_smoke.py -v" || true

# Test 6: Load test
run_test "06" "load_test" \
    "$PYTHON_CMD tests/load/load_test.py" || true

# Test 7: Feature flags
echo "[07] Checking feature flags..."
if [ -n "$DOCKER_PREFIX" ]; then
    $DOCKER_PREFIX python -c "
from core.autonomous.feature_flags import get_feature_flags
flags = get_feature_flags()
print('Feature Flags:')
for name, value in sorted(flags.get_all_flags().items()):
    print(f'  {name}: {value}')
" > "$LOG_DIR/07_feature_flags.log" 2>&1 || true
else
    $PYTHON_CMD -c "
from core.autonomous.feature_flags import get_feature_flags
flags = get_feature_flags()
print('Feature Flags:')
for name, value in sorted(flags.get_all_flags().items()):
    print(f'  {name}: {value}')
" > "$LOG_DIR/07_feature_flags.log" 2>&1 || true
fi
echo "  ✅ Feature flags checked"

# Test 8: Startup validation
echo "[08] Checking startup validation..."
if command -v docker &> /dev/null; then
    docker logs byos_api 2>&1 | grep -A 5 "Production configuration validated" > "$LOG_DIR/08_startup_validation.log" 2>&1 || true
    echo "  ✅ Startup validation checked"
else
    echo "  ⚠️  Docker not available, skipping"
fi

# Test 9: Prometheus metrics
echo "[09] Checking Prometheus metrics..."
curl -s http://localhost:9090/metrics 2>&1 | head -100 > "$LOG_DIR/09_metrics.log" || {
    echo "  ⚠️  Metrics endpoint not accessible"
}

# Test 10: Database connection
echo "[10] Testing database connection..."
if command -v docker &> /dev/null && docker ps | grep -q byos_postgres; then
    docker exec -it byos_postgres psql -U postgres -d byos_ai -c "SELECT COUNT(*) FROM workspaces;" > "$LOG_DIR/10_db_connection.log" 2>&1 || true
    echo "  ✅ Database connection tested"
else
    echo "  ⚠️  PostgreSQL container not found, skipping"
fi

# Generate summary report
echo ""
echo "Generating summary report..."

cat > "$LOG_DIR/VERIFICATION_SUMMARY.md" << EOF
# Staging Deployment Verification Summary

**Date**: $(date)
**Version**: $(git describe --tags 2>/dev/null || echo "unknown")
**Environment**: Staging
**Log Directory**: $LOG_DIR

## Test Results

EOF

# Add test results to summary
for log_file in "$LOG_DIR"/*.log; do
    if [ -f "$log_file" ]; then
        log_name=$(basename "$log_file" .log)
        echo "### $log_name" >> "$LOG_DIR/VERIFICATION_SUMMARY.md"
        echo "" >> "$LOG_DIR/VERIFICATION_SUMMARY.md"
        echo "\`\`\`" >> "$LOG_DIR/VERIFICATION_SUMMARY.md"
        tail -20 "$log_file" >> "$LOG_DIR/VERIFICATION_SUMMARY.md" || true
        echo "\`\`\`" >> "$LOG_DIR/VERIFICATION_SUMMARY.md"
        echo "" >> "$LOG_DIR/VERIFICATION_SUMMARY.md"
    fi
done

cat >> "$LOG_DIR/VERIFICATION_SUMMARY.md" << EOF
## Status Checklist

- [ ] All tests passed
- [ ] No critical errors in logs
- [ ] Feature flags loaded correctly
- [ ] Startup validation passed
- [ ] Metrics endpoint accessible
- [ ] Database connection working

## Next Steps

1. Review all log files in: $LOG_DIR
2. If all checks pass, proceed with canary deployment
3. Archive logs: tar -czf staging-verification-$TIMESTAMP.tar.gz $LOG_DIR

EOF

# Scrub sensitive files from log directory
echo ""
echo "Scrubbing sensitive files from logs..."
find "$LOG_DIR" -name ".env*" -type f -delete || true
find "$LOG_DIR" -name "*.env" -type f -delete || true

# Also scrub from any log files that might contain env vars
if command -v sed &> /dev/null; then
    find "$LOG_DIR" -name "*.log" -type f -exec sed -i.bak \
        -e '/SECRET_KEY=/d' \
        -e '/DATABASE_URL=/d' \
        -e '/.*_API_KEY=/d' \
        -e '/.*_PASSWORD=/d' \
        -e '/.*_SECRET=/d' \
        {} \; || true
    find "$LOG_DIR" -name "*.bak" -delete || true
fi

echo ""
echo "✅ Verification tests complete!"
echo ""
echo "Summary report: $LOG_DIR/VERIFICATION_SUMMARY.md"
echo ""
echo "To archive logs:"
echo "  cd deployment-logs"
echo "  tar -czf staging-verification-$TIMESTAMP.tar.gz $TIMESTAMP"
