#!/bin/bash
# Load Test Runner for BYOS Backend
# Usage: ./load_test.sh -k "byos_your_key" -u 10 -d 60

set -e

API_KEY="${BYOS_API_KEY:-}"
USERS=10
DURATION=60
HOST="http://localhost:8000"

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    -k|--api-key)
      API_KEY="$2"
      shift 2
      ;;
    -u|--users)
      USERS="$2"
      shift 2
      ;;
    -d|--duration)
      DURATION="$2"
      shift 2
      ;;
    -h|--host)
      HOST="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

if [ -z "$API_KEY" ]; then
    echo "❌ Error: API key required. Set BYOS_API_KEY environment variable or pass -k parameter"
    echo "   Example: ./load_test.sh -k 'byos_your_key_here'"
    exit 1
fi

echo "🚀 Starting Locust Load Test"
echo "   Host: $HOST"
echo "   Users: $USERS"
echo "   Duration: ${DURATION}s"
echo ""

# Check if locust is installed
if ! command -v locust &> /dev/null; then
    echo "🔄 Locust not found. Installing..."
    pip install locust
fi

echo "✅ Locust ready"
echo ""
echo "🧪 Starting load test..."
echo "   Web UI: http://localhost:8089"
echo ""

# Run locust
export BYOS_API_KEY="$API_KEY"
locust -f locustfile.py --host "$HOST" --users "$USERS" --spawn-rate 5 --run-time "${DURATION}s" --headless --html load_test_report.html

echo ""
echo "✅ Load test complete!"
echo "   Report saved to: load_test_report.html"
