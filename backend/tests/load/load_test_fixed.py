"""Load test script for autonomous backend - FIXED with proper auth."""
import asyncio
import httpx
import time
from typing import List, Dict
from datetime import datetime, timedelta
import statistics
import jwt
import os
import sys

# Add parent directory to path to import app modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from core.config import get_settings

settings = get_settings()

# Test configuration
BASE_URL = "http://localhost:8000"
WORKSPACE_ID = "test-workspace-load"
USER_ID = "test-user-load"
CONCURRENT_REQUESTS = 100  # 2x expected peak (assuming 50 req/s expected)
REQUESTS_PER_CLIENT = 10
TOTAL_REQUESTS = CONCURRENT_REQUESTS * REQUESTS_PER_CLIENT


def generate_test_token(workspace_id: str = WORKSPACE_ID, user_id: str = USER_ID) -> str:
    """Generate a valid JWT token for load testing."""
    payload = {
        "sub": f"test-{user_id}@example.com",
        "user_id": user_id,
        "workspace_id": workspace_id,
        "exp": datetime.utcnow() + timedelta(hours=1),
        "iat": datetime.utcnow(),
    }
    token = jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)
    return token


async def make_request(
    client: httpx.AsyncClient,
    endpoint: str,
    method: str = "GET",
    json_data: Dict = None,
    headers: Dict = None,
) -> Dict:
    """Make HTTP request and measure latency."""
    start_time = time.time()
    
    try:
        if method == "GET":
            response = await client.get(endpoint, headers=headers, timeout=30.0)
        elif method == "POST":
            response = await client.post(endpoint, json=json_data, headers=headers, timeout=30.0)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        latency_ms = (time.time() - start_time) * 1000
        response.raise_for_status()
        
        return {
            "success": True,
            "status_code": response.status_code,
            "latency_ms": latency_ms,
            "error": None,
        }
    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        return {
            "success": False,
            "status_code": None if not hasattr(e, 'response') else e.response.status_code if hasattr(e.response, 'status_code') else None,
            "latency_ms": latency_ms,
            "error": str(e),
        }


async def test_endpoint(
    endpoint: str,
    method: str = "GET",
    json_data: Dict = None,
    headers: Dict = None,
) -> Dict:
    """Test endpoint under load."""
    print(f"\nTesting {method} {endpoint}...")
    
    async def client_worker(client: httpx.AsyncClient):
        results = []
        for _ in range(REQUESTS_PER_CLIENT):
            result = await make_request(client, endpoint, method, json_data, headers)
            results.append(result)
        return results
    
    # Create clients
    async with httpx.AsyncClient(base_url=BASE_URL) as client:
        # Create tasks for concurrent requests
        tasks = [
            client_worker(client)
            for _ in range(CONCURRENT_REQUESTS)
        ]
        
        # Run all tasks concurrently
        start_time = time.time()
        all_results = await asyncio.gather(*tasks)
        total_time = time.time() - start_time
        
        # Flatten results
        results = [r for client_results in all_results for r in client_results]
    
    # Calculate statistics
    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]
    
    latencies = [r["latency_ms"] for r in successful]
    
    stats = {
        "endpoint": endpoint,
        "method": method,
        "total_requests": len(results),
        "successful": len(successful),
        "failed": len(failed),
        "success_rate": len(successful) / len(results) * 100 if results else 0.0,
        "total_time_seconds": total_time,
        "requests_per_second": len(results) / total_time if total_time > 0 else 0.0,
    }
    
    if latencies:
        stats.update({
            "latency_p50_ms": statistics.median(latencies),
            "latency_p95_ms": statistics.quantiles(latencies, n=20)[18] if len(latencies) >= 20 else max(latencies),
            "latency_p99_ms": statistics.quantiles(latencies, n=100)[98] if len(latencies) >= 100 else max(latencies),
            "latency_min_ms": min(latencies),
            "latency_max_ms": max(latencies),
            "latency_avg_ms": statistics.mean(latencies),
        })
    
    if failed:
        error_counts = {}
        for f in failed:
            error = f["error"] or "unknown"
            error_counts[error] = error_counts.get(error, 0) + 1
        stats["error_breakdown"] = error_counts
    
    return stats


async def run_load_tests():
    """Run load tests for key endpoints."""
    print(f"Load Test Configuration:")
    print(f"  Base URL: {BASE_URL}")
    print(f"  Concurrent Clients: {CONCURRENT_REQUESTS}")
    print(f"  Requests per Client: {REQUESTS_PER_CLIENT}")
    print(f"  Total Requests: {TOTAL_REQUESTS}")
    print(f"  Expected Peak: {CONCURRENT_REQUESTS // 2} req/s")
    print(f"  Testing at: {TOTAL_REQUESTS / 10:.0f} req/s (assuming 10s test)")
    
    # Generate valid JWT token
    token = generate_test_token()
    headers = {
        "Authorization": f"Bearer {token}",
    }
    
    print(f"  Token generated: {token[:50]}...")
    
    # First test health endpoint (no auth required)
    print("\n" + "="*60)
    print("Testing Public Endpoints (No Auth Required)")
    print("="*60)
    
    health_stats = await test_endpoint("/health", "GET", None, {})
    print(f"\nHealth Endpoint:")
    print(f"  Success Rate: {health_stats['success_rate']:.1f}%")
    print(f"  P95 Latency: {health_stats.get('latency_p95_ms', 0):.1f}ms")
    
    status_stats = await test_endpoint("/status", "GET", None, {})
    print(f"\nStatus Endpoint:")
    print(f"  Success Rate: {status_stats['success_rate']:.1f}%")
    print(f"  P95 Latency: {status_stats.get('latency_p95_ms', 0):.1f}ms")
    
    # Test authenticated endpoints
    print("\n" + "="*60)
    print("Testing Authenticated Endpoints")
    print("="*60)
    
    # Test endpoints
    endpoints = [
        # Autonomous ML endpoints
        ("/api/v1/autonomous/cost/predict", "POST", {
            "operation_type": "transcribe",
            "provider": "openai",
            "input_tokens": 1000,
            "estimated_output_tokens": 300,
        }),
        ("/api/v1/autonomous/routing/stats", "GET", {"operation_type": "transcribe"}),
        
        # Insights endpoints
        ("/api/v1/insights/savings", "GET", None),
        ("/api/v1/insights/summary", "GET", None),
        
        # Suggestions endpoints
        ("/api/v1/suggestions", "GET", None),
    ]
    
    all_stats = [health_stats, status_stats]
    
    for endpoint, method, json_data in endpoints:
        try:
            # Build params for GET requests with query params
            actual_endpoint = endpoint
            if method == "GET" and json_data:
                params = "&".join([f"{k}={v}" for k, v in json_data.items()])
                actual_endpoint = f"{endpoint}?{params}"
                json_data = None
            
            stats = await test_endpoint(actual_endpoint, method, json_data, headers)
            all_stats.append(stats)
            
            print(f"\nResults for {method} {endpoint}:")
            print(f"  Success Rate: {stats['success_rate']:.1f}%")
            print(f"  Requests/sec: {stats['requests_per_second']:.1f}")
            if "latency_p95_ms" in stats:
                print(f"  P95 Latency: {stats['latency_p95_ms']:.1f}ms")
                print(f"  P99 Latency: {stats['latency_p99_ms']:.1f}ms")
            if stats["failed"] > 0:
                print(f"  Failed: {stats['failed']} requests")
                if "error_breakdown" in stats:
                    print(f"  Errors: {stats['error_breakdown']}")
        except Exception as e:
            print(f"Error testing {endpoint}: {e}")
    
    # Summary
    print("\n" + "="*60)
    print("LOAD TEST SUMMARY")
    print("="*60)
    
    total_requests = sum(s["total_requests"] for s in all_stats)
    total_successful = sum(s["successful"] for s in all_stats)
    overall_success_rate = (total_successful / total_requests * 100) if total_requests > 0 else 0.0
    
    print(f"Total Requests: {total_requests}")
    print(f"Successful: {total_successful}")
    print(f"Failed: {total_requests - total_successful}")
    print(f"Overall Success Rate: {overall_success_rate:.1f}%")
    
    # Check if tests passed
    if overall_success_rate >= 95.0:
        print("\n✅ LOAD TEST PASSED: Success rate >= 95%")
    else:
        print(f"\n❌ LOAD TEST FAILED: Success rate {overall_success_rate:.1f}% < 95%")
    
    # Check latency thresholds
    p95_latencies = [s.get("latency_p95_ms", 0) for s in all_stats if "latency_p95_ms" in s]
    if p95_latencies:
        max_p95 = max(p95_latencies)
        if max_p95 <= 2000:  # 2 seconds
            print(f"✅ LATENCY TEST PASSED: Max P95 latency {max_p95:.1f}ms <= 2000ms")
        else:
            print(f"❌ LATENCY TEST FAILED: Max P95 latency {max_p95:.1f}ms > 2000ms")
    
    # Return overall success for CI/CD
    return overall_success_rate >= 95.0


if __name__ == "__main__":
    success = asyncio.run(run_load_tests())
    sys.exit(0 if success else 1)
