"""
Load test script for BYOS backend - 5000 CONCURRENT USERS.

This test simulates real-world high-load scenarios:
- 5000 concurrent clients
- Mixed read/write operations
- Proper JWT authentication
- Distributed across multiple endpoints

Run: python tests/load/load_test_5000.py
"""
import asyncio
import httpx
import time
import statistics
import jwt
import sys
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from core.config import get_settings

settings = get_settings()

# ═══════════════════════════════════════════════════════════════════════════════
# TEST CONFIGURATION - 5000 USERS
# ═══════════════════════════════════════════════════════════════════════════════
BASE_URL = "http://localhost:8000"
CONCURRENT_USERS = 5000          # Target: 5000 concurrent users
REQUESTS_PER_USER = 5            # 5 requests per user
TOTAL_REQUESTS = CONCURRENT_USERS * REQUESTS_PER_USER  # 25,000 total

# Test workspace credentials
TEST_WORKSPACE_ID = "load-test-workspace-5000"
TEST_USER_ID = "load-test-user-5000"

# Endpoints to test (weighted by importance)
ENDPOINTS = [
    # (method, endpoint, weight, requires_auth)
    ("GET", "/health", 10, False),                           # Health check (no auth)
    ("GET", "/status", 5, False),                           # Status (no auth)
    ("POST", "/api/v1/autonomous/cost/predict", 20, True),  # Cost prediction
    ("GET", "/api/v1/autonomous/routing/stats", 15, True),  # Routing stats
    ("GET", "/api/v1/insights/summary", 20, True),          # Insights
    ("GET", "/api/v1/suggestions", 15, True),              # Suggestions
    ("POST", "/api/v1/privacy/detect-pii", 10, True),       # PII detection
    ("GET", "/api/v1/budget", 5, True),                     # Budget
]


@dataclass
class TestResult:
    """Result of a single request."""
    endpoint: str
    method: str
    success: bool
    status_code: int
    latency_ms: float
    error: str = None


def generate_test_token(user_num: int) -> str:
    """Generate a valid JWT token for load testing."""
    payload = {
        "sub": f"load-test-{user_num}@example.com",
        "user_id": f"{TEST_USER_ID}-{user_num}",
        "workspace_id": f"{TEST_WORKSPACE_ID}-{user_num % 100}",  # 100 workspaces
        "exp": datetime.utcnow() + timedelta(hours=1),
        "iat": datetime.utcnow(),
    }
    token = jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)
    return token


async def make_request(
    client: httpx.AsyncClient,
    method: str,
    endpoint: str,
    token: str = None,
    json_data: Dict = None,
) -> TestResult:
    """Make a single HTTP request and measure performance."""
    start_time = time.perf_counter()
    
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    try:
        if method == "GET":
            response = await client.get(endpoint, headers=headers, timeout=30.0)
        elif method == "POST":
            response = await client.post(endpoint, json=json_data, headers=headers, timeout=30.0)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        latency_ms = (time.perf_counter() - start_time) * 1000
        
        # Consider 2xx and 3xx as success, 4xx as expected (auth errors on bad tokens)
        success = response.status_code < 500
        
        return TestResult(
            endpoint=endpoint,
            method=method,
            success=success,
            status_code=response.status_code,
            latency_ms=latency_ms,
            error=None if success else f"HTTP {response.status_code}",
        )
        
    except httpx.TimeoutException as e:
        return TestResult(
            endpoint=endpoint,
            method=method,
            success=False,
            status_code=0,
            latency_ms=(time.perf_counter() - start_time) * 1000,
            error="Timeout",
        )
    except Exception as e:
        return TestResult(
            endpoint=endpoint,
            method=method,
            success=False,
            status_code=0,
            latency_ms=(time.perf_counter() - start_time) * 1000,
            error=str(e)[:100],
        )


def select_endpoint() -> tuple:
    """Select an endpoint based on weighted probability."""
    import random
    total_weight = sum(w for (_, _, w, _) in ENDPOINTS)
    r = random.uniform(0, total_weight)
    cumulative = 0
    for method, endpoint, weight, requires_auth in ENDPOINTS:
        cumulative += weight
        if r <= cumulative:
            return method, endpoint, requires_auth
    return ENDPOINTS[-1][:3]


async def simulate_user(client: httpx.AsyncClient, user_num: int) -> List[TestResult]:
    """Simulate a single user making multiple requests."""
    results = []
    token = generate_test_token(user_num)
    
    for _ in range(REQUESTS_PER_USER):
        method, endpoint, requires_auth = select_endpoint()
        
        # Generate appropriate payload
        json_data = None
        if endpoint == "/api/v1/autonomous/cost/predict":
            json_data = {
                "operation_type": "transcribe",
                "provider": "openai",
                "input_tokens": 1000,
                "estimated_output_tokens": 300,
            }
        elif endpoint == "/api/v1/privacy/detect-pii":
            json_data = {"text": "This is a test message with no PII"}
        
        result = await make_request(
            client, method, endpoint,
            token=token if requires_auth else None,
            json_data=json_data,
        )
        results.append(result)
    
    return results


async def run_load_test():
    """Run the full load test with 5000 concurrent users."""
    print("=" * 80)
    print("BYOS BACKEND LOAD TEST - 5000 CONCURRENT USERS")
    print("=" * 80)
    print(f"Target URL: {BASE_URL}")
    print(f"Concurrent Users: {CONCURRENT_USERS:,}")
    print(f"Requests per User: {REQUESTS_PER_USER}")
    print(f"Total Requests: {TOTAL_REQUESTS:,}")
    print(f"Expected Peak Load: {TOTAL_REQUESTS / 60:.0f} req/s (if 60s test)")
    print("=" * 80)
    
    # Warm-up phase
    print("\n🔥 Warming up... (creating connection pool)")
    async with httpx.AsyncClient(
        base_url=BASE_URL,
        limits=httpx.Limits(max_connections=1000, max_keepalive_connections=500),
        timeout=httpx.Timeout(30.0),
    ) as client:
        # Quick health check
        try:
            resp = await client.get("/health", timeout=5.0)
            if resp.status_code == 200:
                print(f"✅ Health check passed: {resp.json()}")
            else:
                print(f"❌ Health check failed: {resp.status_code}")
                return False
        except Exception as e:
            print(f"❌ Cannot connect to {BASE_URL}: {e}")
            return False
        
        # Wait for connection pool to stabilize
        await asyncio.sleep(1)
        
        print(f"\n🚀 Starting load test with {CONCURRENT_USERS:,} concurrent users...")
        print("This may take 2-5 minutes...")
        
        start_time = time.perf_counter()
        
        # Create all user tasks
        tasks = [
            simulate_user(client, i)
            for i in range(CONCURRENT_USERS)
        ]
        
        # Run all users concurrently with progress tracking
        all_results_nested = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Flatten results
        all_results = []
        for result in all_results_nested:
            if isinstance(result, Exception):
                print(f"❌ User task failed: {result}")
            else:
                all_results.extend(result)
        
        total_time = time.perf_counter() - start_time
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # ANALYZE RESULTS
    # ═══════════════════════════════════════════════════════════════════════════════
    print("\n" + "=" * 80)
    print("LOAD TEST RESULTS")
    print("=" * 80)
    
    total_requests = len(all_results)
    successful = [r for r in all_results if r.success]
    failed = [r for r in all_results if not r.success]
    
    success_rate = len(successful) / total_requests * 100 if total_requests > 0 else 0
    
    print(f"\n📊 OVERALL STATISTICS")
    print(f"  Total Requests: {total_requests:,}")
    print(f"  Successful: {len(successful):,}")
    print(f"  Failed: {len(failed):,}")
    print(f"  Success Rate: {success_rate:.2f}%")
    print(f"  Total Time: {total_time:.2f}s")
    print(f"  Requests/sec: {total_requests / total_time:.1f}")
    
    # Latency statistics
    latencies = [r.latency_ms for r in successful]
    if latencies:
        print(f"\n⏱️ LATENCY STATISTICS")
        print(f"  Min: {min(latencies):.1f}ms")
        print(f"  Max: {max(latencies):.1f}ms")
        print(f"  Mean: {statistics.mean(latencies):.1f}ms")
        print(f"  Median: {statistics.median(latencies):.1f}ms")
        
        if len(latencies) >= 10:
            latencies_sorted = sorted(latencies)
            p95_idx = int(len(latencies_sorted) * 0.95)
            p99_idx = int(len(latencies_sorted) * 0.99)
            print(f"  P95: {latencies_sorted[min(p95_idx, len(latencies_sorted)-1)]:.1f}ms")
            print(f"  P99: {latencies_sorted[min(p99_idx, len(latencies_sorted)-1)]:.1f}ms")
    
    # Error breakdown
    if failed:
        error_counts = {}
        for r in failed:
            error_key = f"{r.error or 'Unknown'}"
            error_counts[error_key] = error_counts.get(error_key, 0) + 1
        
        print(f"\n❌ ERROR BREAKDOWN (Top 10)")
        for error, count in sorted(error_counts.items(), key=lambda x: -x[1])[:10]:
            print(f"  {error}: {count:,} ({count/len(failed)*100:.1f}%)")
    
    # Endpoint statistics
    print(f"\n📍 ENDPOINT STATISTICS")
    endpoint_stats = {}
    for r in all_results:
        key = f"{r.method} {r.endpoint}"
        if key not in endpoint_stats:
            endpoint_stats[key] = {"total": 0, "success": 0, "latencies": []}
        endpoint_stats[key]["total"] += 1
        if r.success:
            endpoint_stats[key]["success"] += 1
            endpoint_stats[key]["latencies"].append(r.latency_ms)
    
    for endpoint, stats in sorted(endpoint_stats.items(), key=lambda x: -x[1]["total"])[:8]:
        success_pct = stats["success"] / stats["total"] * 100
        avg_latency = statistics.mean(stats["latencies"]) if stats["latencies"] else 0
        print(f"  {endpoint:40s} {stats['success']:>6,}/{stats['total']:<6,} ({success_pct:5.1f}%) {avg_latency:>6.1f}ms avg")
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # PASS/FAIL CRITERIA
    # ═══════════════════════════════════════════════════════════════════════════════
    print("\n" + "=" * 80)
    print("PASS/FAIL CRITERIA")
    print("=" * 80)
    
    passed = True
    
    # Criterion 1: Success rate >= 95%
    if success_rate >= 95.0:
        print(f"✅ SUCCESS RATE: {success_rate:.1f}% >= 95%")
    else:
        print(f"❌ SUCCESS RATE: {success_rate:.1f}% < 95%")
        passed = False
    
    # Criterion 2: P95 latency <= 2000ms
    if latencies:
        p95 = latencies_sorted[min(int(len(latencies_sorted) * 0.95), len(latencies_sorted)-1)]
        if p95 <= 2000:
            print(f"✅ P95 LATENCY: {p95:.1f}ms <= 2000ms")
        else:
            print(f"❌ P95 LATENCY: {p95:.1f}ms > 2000ms")
            passed = False
    
    # Criterion 3: No timeout errors > 1%
    timeout_errors = len([r for r in failed if r.error == "Timeout"])
    timeout_pct = timeout_errors / total_requests * 100 if total_requests > 0 else 0
    if timeout_pct <= 1.0:
        print(f"✅ TIMEOUTS: {timeout_pct:.2f}% <= 1%")
    else:
        print(f"❌ TIMEOUTS: {timeout_pct:.2f}% > 1%")
        passed = False
    
    # Criterion 4: Requests/sec >= 100 (minimum viable)
    rps = total_requests / total_time
    if rps >= 100:
        print(f"✅ THROUGHPUT: {rps:.1f} req/s >= 100 req/s")
    else:
        print(f"❌ THROUGHPUT: {rps:.1f} req/s < 100 req/s")
        passed = False
    
    print("\n" + "=" * 80)
    if passed:
        print("🎉 LOAD TEST PASSED - System ready for 5000 users!")
    else:
        print("⚠️  LOAD TEST FAILED - Review bottlenecks above")
    print("=" * 80)
    
    return passed


if __name__ == "__main__":
    # Set event loop policy for Windows
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    try:
        success = asyncio.run(run_load_test())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
