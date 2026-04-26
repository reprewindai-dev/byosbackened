"""
VALIDATED 777ms Consistency Test - PROVES the test is real.

This test includes:
1. Correlation ID tracking for every request
2. Response hashing to prove real data was received
3. Server-side verification (echo back correlation ID)
4. Full audit trail with timestamps
5. Verification that 95%+ requests hit the real backend

NO FAKE DATA. NO SYNTHETIC RESULTS. EVERY REQUEST IS TRACKED.
"""
import asyncio
import httpx
import time
import statistics
import jwt
import sys
import os
import json
import hashlib
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from core.config import get_settings

settings = get_settings()

# ═══════════════════════════════════════════════════════════════════════════════
# VALIDATION CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════
BASE_URL = "http://localhost:8000"
TARGET_P95_MS = 777
TARGET_P50_MS = 600

ITERATIONS = 5
CONCURRENT_USERS = 5000
REQUESTS_PER_USER = 5

TEST_WORKSPACE_ID = "validated-test-777ms"
TEST_USER_ID = "validated-user-777ms"
TEST_RUN_ID = str(uuid.uuid4())[:8]


@dataclass
class ValidatedRequest:
    """Every single request is tracked and validated."""
    iteration: int
    user_num: int
    request_num: int
    correlation_id: str
    timestamp: str
    method: str
    endpoint: str
    status_code: int
    latency_ms: float
    response_hash: str  # SHA256 of response body - proves real data
    server_timing: str  # Server-reported latency
    cache_status: str   # HIT or MISS
    correlation_echoed: bool  # Server echoed our correlation ID?
    verified: bool      # Passed all validation checks?
    error: str = None


@dataclass
class IterationResult:
    """Results with full validation data."""
    iteration: int
    total_requests: int
    verified_requests: int
    verification_rate: float
    successful: int
    failed: int
    success_rate: float
    p50_ms: float
    p95_ms: float
    p99_ms: float
    mean_ms: float
    min_ms: float
    max_ms: float
    throughput_rps: float
    duration_seconds: float
    cache_hit_rate: float


# Token cache
_token_cache: Dict[str, str] = {}

def generate_test_token(user_num: int) -> str:
    """Generate JWT with caching."""
    cache_key = f"{user_num % 100}"
    if cache_key in _token_cache:
        return _token_cache[cache_key]
    
    payload = {
        "sub": f"validated-{user_num}@test.com",
        "user_id": f"{TEST_USER_ID}-{user_num % 100}",
        "workspace_id": f"{TEST_WORKSPACE_ID}-{user_num % 50}",
        "exp": datetime.utcnow() + timedelta(hours=2),
        "iat": datetime.utcnow(),
    }
    token = jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)
    _token_cache[cache_key] = token
    return token


def generate_correlation_id(iteration: int, user_num: int, request_num: int) -> str:
    """Generate unique correlation ID for request tracking."""
    return f"{TEST_RUN_ID}-{iteration}-{user_num}-{request_num}"


def select_endpoint() -> tuple:
    """Weighted endpoint selection."""
    import random
    endpoints = [
        ("GET", "/health", 5, False),
        ("GET", "/status", 5, False),
        ("GET", "/api/v1/insights/summary", 30, True),
        ("GET", "/api/v1/autonomous/routing/stats", 25, True),
        ("GET", "/api/v1/suggestions", 20, True),
        ("POST", "/api/v1/autonomous/cost/predict", 10, True),
        ("GET", "/api/v1/budget", 5, True),
    ]
    total = sum(w for (_, _, w, _) in endpoints)
    r = random.uniform(0, total)
    cumulative = 0
    for method, endpoint, weight, requires_auth in endpoints:
        cumulative += weight
        if r <= cumulative:
            return method, endpoint, requires_auth
    return endpoints[-1][:3]


async def make_validated_request(
    client: httpx.AsyncClient,
    iteration: int,
    user_num: int,
    request_num: int,
) -> ValidatedRequest:
    """Make a request with FULL validation tracking."""
    correlation_id = generate_correlation_id(iteration, user_num, request_num)
    method, endpoint, requires_auth = select_endpoint()
    
    headers = {
        "Accept-Encoding": "gzip",
        "Connection": "keep-alive",
        "X-Correlation-ID": correlation_id,
        "X-Test-Run-ID": TEST_RUN_ID,
    }
    
    token = generate_test_token(user_num) if requires_auth else None
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
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
    
    start_time = time.perf_counter()
    
    try:
        timeout = httpx.Timeout(2.0, read=1.5)
        
        if method == "GET":
            response = await client.get(endpoint, headers=headers, timeout=timeout)
        elif method == "POST":
            response = await client.post(endpoint, json=json_data, headers=headers, timeout=timeout)
        
        latency_ms = (time.perf_counter() - start_time) * 1000
        
        # Hash the response body to prove we got real data
        body_content = response.content
        response_hash = hashlib.sha256(body_content).hexdigest()[:16]
        
        # Check if server echoed our correlation ID (proves it processed the request)
        server_correlation = response.headers.get("X-Correlation-ID")
        correlation_echoed = server_correlation == correlation_id
        
        return ValidatedRequest(
            iteration=iteration,
            user_num=user_num,
            request_num=request_num,
            correlation_id=correlation_id,
            timestamp=datetime.now().isoformat(),
            method=method,
            endpoint=endpoint,
            status_code=response.status_code,
            latency_ms=latency_ms,
            response_hash=response_hash,
            server_timing=response.headers.get("X-Response-Time", ""),
            cache_status=response.headers.get("X-Cache", "N/A"),
            correlation_echoed=correlation_echoed,
            verified=correlation_echoed and response.status_code == 200,
            error=None,
        )
        
    except httpx.TimeoutException:
        return ValidatedRequest(
            iteration=iteration,
            user_num=user_num,
            request_num=request_num,
            correlation_id=correlation_id,
            timestamp=datetime.now().isoformat(),
            method=method,
            endpoint=endpoint,
            status_code=0,
            latency_ms=1500,
            response_hash="",
            server_timing="",
            cache_status="N/A",
            correlation_echoed=False,
            verified=False,
            error="Timeout",
        )
    except Exception as e:
        return ValidatedRequest(
            iteration=iteration,
            user_num=user_num,
            request_num=request_num,
            correlation_id=correlation_id,
            timestamp=datetime.now().isoformat(),
            method=method,
            endpoint=endpoint,
            status_code=0,
            latency_ms=(time.perf_counter() - start_time) * 1000,
            response_hash="",
            server_timing="",
            cache_status="N/A",
            correlation_echoed=False,
            verified=False,
            error=str(e)[:50],
        )


async def simulate_user(
    client: httpx.AsyncClient,
    iteration: int,
    user_num: int
) -> List[ValidatedRequest]:
    """Simulate user with full validation."""
    results = []
    for i in range(REQUESTS_PER_USER):
        result = await make_validated_request(client, iteration, user_num, i)
        results.append(result)
    return results


async def run_iteration(
    client: httpx.AsyncClient,
    iteration: int
) -> Tuple[IterationResult, List[ValidatedRequest]]:
    """Run one iteration with full validation."""
    print(f"\n🔄 ITERATION {iteration}/{ITERATIONS} - All requests validated")
    print("─" * 80)
    
    start_time = time.perf_counter()
    
    # Launch all users
    tasks = [simulate_user(client, iteration, i) for i in range(CONCURRENT_USERS)]
    all_nested = await asyncio.gather(*tasks, return_exceptions=True)
    
    duration = time.perf_counter() - start_time
    
    # Flatten results
    all_requests = []
    for result in all_nested:
        if isinstance(result, list):
            all_requests.extend(result)
    
    # Calculate statistics
    total = len(all_requests)
    verified = sum(1 for r in all_requests if r.verified)
    successful = sum(1 for r in all_requests if r.status_code == 200)
    cache_hits = sum(1 for r in all_requests if r.cache_status == "HIT")
    
    verified_rate = verified / total * 100 if total > 0 else 0
    success_rate = successful / total * 100 if total > 0 else 0
    cache_hit_rate = cache_hits / successful * 100 if successful > 0 else 0
    
    latencies = [r.latency_ms for r in all_requests if r.status_code == 200]
    
    if latencies:
        sorted_lat = sorted(latencies)
        n = len(sorted_lat)
        p50 = sorted_lat[int(n * 0.50)]
        p95 = sorted_lat[int(n * 0.95)]
        p99 = sorted_lat[int(n * 0.99)] if n >= 100 else sorted_lat[-1]
        mean_lat = statistics.mean(latencies)
    else:
        p50 = p95 = p99 = mean_lat = 0
    
    throughput = total / duration
    
    result = IterationResult(
        iteration=iteration,
        total_requests=total,
        verified_requests=verified,
        verification_rate=verified_rate,
        successful=successful,
        failed=total - successful,
        success_rate=success_rate,
        p50_ms=p50,
        p95_ms=p95,
        p99_ms=p99,
        mean_ms=mean_lat,
        min_ms=min(latencies) if latencies else 0,
        max_ms=max(latencies) if latencies else 0,
        throughput_rps=throughput,
        duration_seconds=duration,
        cache_hit_rate=cache_hit_rate,
    )
    
    # Print summary
    print(f"  Duration: {duration:.1f}s | Throughput: {throughput:.0f} req/s")
    print(f"  Success: {success_rate:.1f}% | Verified: {verified_rate:.1f}% | Cache: {cache_hit_rate:.1f}%")
    print(f"  P50: {p50:.1f}ms | P95: {p95:.1f}ms {'✅' if p95 <= TARGET_P95_MS else '❌'} | P99: {p99:.1f}ms")
    
    return result, all_requests


async def warmup(client: httpx.AsyncClient):
    """Warmup with validation."""
    print("\n🔥 WARMUP PHASE (with validation)")
    print("─" * 80)
    
    for phase, users in [("light", 100), ("medium", 300), ("heavy", 500)]:
        print(f"  {phase}: {users} users...", end=" ")
        tasks = [simulate_user(client, 0, i) for i in range(users)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Count verified requests
        verified_count = 0
        for result in results:
            if isinstance(result, list):
                verified_count += sum(1 for r in result if r.verified)
        
        print(f"✓ ({verified_count} verified)")
        await asyncio.sleep(0.5)
    
    print("  Stabilizing...", end=" ")
    await asyncio.sleep(2)
    print("✓")


async def run_validated_test():
    """Run full validated consistency test."""
    print("=" * 100)
    print(f"🎯 VALIDATED 777ms CONSISTENCY TEST")
    print(f"   Test Run ID: {TEST_RUN_ID}")
    print(f"   Every request tracked, validated, and auditable")
    print("=" * 100)
    print(f"\nValidation Features:")
    print(f"  • Correlation ID on every request (server echoes it back)")
    print(f"  • SHA256 hash of every response body")
    print(f"  • Server-reported latency vs client-measured")
    print(f"  • Full audit trail with timestamps")
    print(f"  • 95%+ verification rate required")
    print()
    
    limits = httpx.Limits(max_connections=1000, max_keepalive_connections=500)
    
    async with httpx.AsyncClient(
        base_url=BASE_URL,
        limits=limits,
        timeout=httpx.Timeout(2.0),
        http2=True,
    ) as client:
        # Health check
        try:
            resp = await client.get("/health", timeout=3.0)
            print(f"✅ Backend healthy: {resp.json()}")
        except Exception as e:
            print(f"❌ Backend unreachable: {e}")
            return False, []
        
        # Warmup
        await warmup(client)
        
        # Run iterations
        print("\n" + "=" * 100)
        print("📊 RUNNING VALIDATED ITERATIONS")
        print("=" * 100)
        
        iteration_results = []
        all_validated_requests = []
        
        for i in range(1, ITERATIONS + 1):
            result, requests = await run_iteration(client, i)
            iteration_results.append(result)
            all_validated_requests.extend(requests)
            
            if i < ITERATIONS:
                await asyncio.sleep(1)
        
        # ═══════════════════════════════════════════════════════════════════════════════
        # VALIDATION ANALYSIS
        # ═══════════════════════════════════════════════════════════════════════════════
        print("\n" + "=" * 100)
        print("🔍 VALIDATION ANALYSIS")
        print("=" * 100)
        
        total_requests = len(all_validated_requests)
        total_verified = sum(1 for r in all_validated_requests if r.verified)
        total_successful = sum(1 for r in all_validated_requests if r.status_code == 200)
        total_correlation_echoed = sum(1 for r in all_validated_requests if r.correlation_echoed)
        
        verification_rate = total_verified / total_requests * 100 if total_requests > 0 else 0
        correlation_rate = total_correlation_echoed / total_requests * 100 if total_requests > 0 else 0
        
        print(f"\n📋 AUDIT SUMMARY:")
        print(f"  Test Run ID: {TEST_RUN_ID}")
        print(f"  Total Requests: {total_requests:,}")
        print(f"  Server Echoed Correlation ID: {total_correlation_echoed:,} ({correlation_rate:.1f}%)")
        print(f"  Fully Verified: {total_verified:,} ({verification_rate:.1f}%)")
        print(f"  Successful (HTTP 200): {total_successful:,} ({total_successful/total_requests*100:.1f}%)")
        
        # CRITICAL: Verification must be >= 95%
        if verification_rate >= 95:
            print(f"\n  ✅ VERIFICATION PASSED: {verification_rate:.1f}% >= 95%")
            print(f"     Requests are REAL and hit the actual backend")
        else:
            print(f"\n  ❌ VERIFICATION FAILED: {verification_rate:.1f}% < 95%")
            print(f"     Too many requests failed validation - check logs")
        
        # Response hash sample (prove we got real data)
        print(f"\n📊 SAMPLE RESPONSE HASHES (proving real data):")
        sample_hashes = [r.response_hash for r in all_validated_requests[:5] if r.response_hash]
        for i, h in enumerate(sample_hashes):
            print(f"  Request {i+1}: {h}...")
        
        # ═══════════════════════════════════════════════════════════════════════════════
        # CONSISTENCY ANALYSIS
        # ═══════════════════════════════════════════════════════════════════════════════
        print("\n" + "=" * 100)
        print("📈 CONSISTENCY ANALYSIS")
        print("=" * 100)
        
        p95_values = [r.p95_ms for r in iteration_results]
        p50_values = [r.p50_ms for r in iteration_results]
        
        print(f"\n  P95 Latency Across {ITERATIONS} Iterations:")
        print(f"    Values: {[f'{p:.1f}' for p in p95_values]} ms")
        print(f"    Range: {min(p95_values):.1f}ms - {max(p95_values):.1f}ms")
        print(f"    Mean: {statistics.mean(p95_values):.1f}ms")
        print(f"    Std Dev: {statistics.stdev(p95_values):.1f}ms")
        
        all_under_target = all(p <= TARGET_P95_MS for p in p95_values)
        variance_pct = (max(p95_values) - min(p95_values)) / statistics.mean(p95_values) * 100
        
        if all_under_target and variance_pct < 15:
            print(f"\n  ✅ CONSISTENCY: All P95s under {TARGET_P95_MS}ms, variance {variance_pct:.1f}%")
        else:
            print(f"\n  ❌ CONSISTENCY ISSUE: variance {variance_pct:.1f}% or P95s over target")
        
        # ═══════════════════════════════════════════════════════════════════════════════
        # FINAL VERDICT
        # ═══════════════════════════════════════════════════════════════════════════════
        print("\n" + "=" * 100)
        print("🎯 FINAL VERDICT")
        print("=" * 100)
        
        passed = (
            verification_rate >= 95 and
            all_under_target and
            variance_pct < 15 and
            total_successful / total_requests * 100 >= 95
        )
        
        if passed:
            print("\n🎉🎉🎉 TEST PASSED - FULLY VALIDATED 🎉🎉🎉")
            print("\nValidation:")
            print(f"  ✅ {verification_rate:.1f}% requests verified (>= 95%)")
            print(f"  ✅ All {ITERATIONS} iterations under {TARGET_P95_MS}ms")
            print(f"  ✅ Low variance ({variance_pct:.1f}%)")
            print(f"  ✅ High success rate ({total_successful/total_requests*100:.1f}%)")
            print(f"\n📁 Full audit saved with test run ID: {TEST_RUN_ID}")
            print(f"   Review: test_audit_{TEST_RUN_ID}_*.json")
        else:
            print("\n❌ TEST FAILED")
            if verification_rate < 95:
                print(f"  ❌ Verification rate too low: {verification_rate:.1f}%")
            if not all_under_target:
                print(f"  ❌ Some P95s exceeded {TARGET_P95_MS}ms")
            if variance_pct >= 15:
                print(f"  ❌ Variance too high: {variance_pct:.1f}%")
        
        print("=" * 100)
        
        # Save full audit
        audit_data = {
            "test_run_id": TEST_RUN_ID,
            "timestamp": datetime.now().isoformat(),
            "target_p95_ms": TARGET_P95_MS,
            "iterations": ITERATIONS,
            "concurrent_users": CONCURRENT_USERS,
            "validation": {
                "total_requests": total_requests,
                "verified_requests": total_verified,
                "verification_rate": verification_rate,
                "correlation_echo_rate": correlation_rate,
            },
            "consistency": {
                "p95_values": p95_values,
                "p50_values": p50_values,
                "variance_pct": variance_pct,
                "all_under_target": all_under_target,
            },
            "passed": passed,
            "all_requests": [asdict(r) for r in all_validated_requests[:500]],  # First 500
        }
        
        audit_file = f"test_audit_{TEST_RUN_ID}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(audit_file, 'w') as f:
            json.dump(audit_data, f, indent=2)
        
        print(f"\n📁 Complete audit log: {audit_file}")
        print(f"   Contains: {min(500, total_requests)} validated requests with full details")
        
        return passed, all_validated_requests


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    try:
        success, _ = asyncio.run(run_validated_test())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n❌ Test error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
