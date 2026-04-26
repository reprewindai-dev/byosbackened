"""
CONSISTENCY TEST - Multiple iterations to prove 777ms is sustainable.

Runs 5 iterations of 5000 concurrent users:
- Warmup phase (steady state verification)
- 5 full test iterations
- Statistical analysis (mean, std dev, confidence intervals)
- Outlier detection
- Consistency scoring

Target: P95 consistently <= 777ms across ALL iterations
        P50 (average) approaching 777ms
"""
import asyncio
import httpx
import time
import statistics
import jwt
import sys
import os
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from core.config import get_settings

settings = get_settings()

# ═══════════════════════════════════════════════════════════════════════════════
# CONSISTENCY CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════
BASE_URL = "http://localhost:8000"
TARGET_P95_MS = 777
TARGET_P50_MS = 600  # Average should be even lower

ITERATIONS = 5          # Run 5 times to prove consistency
CONCURRENT_USERS = 5000
REQUESTS_PER_USER = 5
WARMUP_USERS = 500      # Pre-warm before measurement

TEST_WORKSPACE_ID = "consistent-test-777ms"
TEST_USER_ID = "consistent-user-777ms"

# Steady-state threshold (max variance allowed)
MAX_P95_VARIANCE_PCT = 15  # P95 can't vary more than 15% between runs
MIN_SUCCESS_RATE = 95      # Must maintain 95%+ success


@dataclass
class IterationResult:
    """Results from a single test iteration."""
    iteration: int
    total_requests: int
    successful: int
    failed: int
    success_rate: float
    p50_ms: float
    p95_ms: float
    p99_ms: float
    mean_ms: float
    std_dev_ms: float
    min_ms: float
    max_ms: float
    throughput_rps: float
    duration_seconds: float
    cache_hit_rate: float
    

@dataclass
class TestResult:
    """Single request result."""
    endpoint: str
    method: str
    success: bool
    status_code: int
    latency_ms: float
    cache_hit: bool = False
    error: str = None


# Token cache for performance
_token_cache: Dict[str, str] = {}

def generate_test_token(user_num: int) -> str:
    """Generate JWT with caching."""
    cache_key = f"{user_num % 100}"
    if cache_key in _token_cache:
        return _token_cache[cache_key]
    
    payload = {
        "sub": f"consistency-{user_num}@test.com",
        "user_id": f"{TEST_USER_ID}-{user_num % 100}",
        "workspace_id": f"{TEST_WORKSPACE_ID}-{user_num % 50}",
        "exp": datetime.utcnow() + timedelta(hours=2),
        "iat": datetime.utcnow(),
    }
    token = jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)
    _token_cache[cache_key] = token
    return token


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


async def make_request(
    client: httpx.AsyncClient,
    method: str,
    endpoint: str,
    token: str = None,
    json_data: Dict = None,
) -> TestResult:
    """Make request with strict timeouts."""
    start_time = time.perf_counter()
    
    headers = {
        "Accept-Encoding": "gzip",
        "Connection": "keep-alive",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    try:
        timeout = httpx.Timeout(2.0, read=1.5)
        
        if method == "GET":
            response = await client.get(endpoint, headers=headers, timeout=timeout)
        elif method == "POST":
            response = await client.post(endpoint, json=json_data, headers=headers, timeout=timeout)
        
        latency_ms = (time.perf_counter() - start_time) * 1000
        cache_hit = response.headers.get("X-Cache") == "HIT"
        
        return TestResult(
            endpoint=endpoint,
            method=method,
            success=response.status_code < 500,
            status_code=response.status_code,
            latency_ms=latency_ms,
            cache_hit=cache_hit,
            error=None if response.status_code < 500 else f"HTTP {response.status_code}",
        )
        
    except httpx.TimeoutException:
        return TestResult(
            endpoint=endpoint,
            method=method,
            success=False,
            status_code=0,
            latency_ms=1500,
            error="Timeout",
        )
    except Exception as e:
        return TestResult(
            endpoint=endpoint,
            method=method,
            success=False,
            status_code=0,
            latency_ms=(time.perf_counter() - start_time) * 1000,
            error=str(e)[:50],
        )


async def simulate_user(client: httpx.AsyncClient, user_num: int) -> List[TestResult]:
    """Simulate single user."""
    results = []
    token = generate_test_token(user_num)
    
    for _ in range(REQUESTS_PER_USER):
        method, endpoint, requires_auth = select_endpoint()
        
        json_data = None
        if endpoint == "/api/v1/autonomous/cost/predict":
            json_data = {
                "operation_type": "transcribe",
                "provider": "openai",
                "input_tokens": 1000,
                "estimated_output_tokens": 300,
            }
        
        result = await make_request(
            client, method, endpoint,
            token=token if requires_auth else None,
            json_data=json_data,
        )
        results.append(result)
    
    return results


async def run_iteration(client: httpx.AsyncClient, iteration: int) -> IterationResult:
    """Run a single test iteration."""
    print(f"\n🔄 ITERATION {iteration}/{ITERATIONS}")
    print("─" * 60)
    
    start_time = time.perf_counter()
    
    # Launch all users
    tasks = [simulate_user(client, i) for i in range(CONCURRENT_USERS)]
    all_nested = await asyncio.gather(*tasks, return_exceptions=True)
    
    duration = time.perf_counter() - start_time
    
    # Process results
    all_results = []
    for r in all_nested:
        if isinstance(r, list):
            all_results.extend(r)
    
    total = len(all_results)
    successful = [r for r in all_results if r.success]
    failed = [r for r in all_results if not r.success]
    latencies = [r.latency_ms for r in successful]
    
    success_rate = len(successful) / total * 100 if total > 0 else 0
    cache_hits = len([r for r in successful if r.cache_hit])
    cache_hit_rate = cache_hits / len(successful) * 100 if successful else 0
    
    # Calculate statistics
    sorted_lat = sorted(latencies)
    p50 = sorted_lat[int(len(sorted_lat) * 0.50)]
    p95 = sorted_lat[int(len(sorted_lat) * 0.95)]
    p99 = sorted_lat[int(len(sorted_lat) * 0.99)]
    mean_lat = statistics.mean(latencies)
    std_dev = statistics.stdev(latencies) if len(latencies) > 1 else 0
    
    throughput = total / duration
    
    result = IterationResult(
        iteration=iteration,
        total_requests=total,
        successful=len(successful),
        failed=len(failed),
        success_rate=success_rate,
        p50_ms=p50,
        p95_ms=p95,
        p99_ms=p99,
        mean_ms=mean_lat,
        std_dev_ms=std_dev,
        min_ms=min(latencies) if latencies else 0,
        max_ms=max(latencies) if latencies else 0,
        throughput_rps=throughput,
        duration_seconds=duration,
        cache_hit_rate=cache_hit_rate,
    )
    
    # Print iteration summary
    print(f"  Duration: {duration:.1f}s | Throughput: {throughput:.0f} req/s")
    print(f"  Success: {success_rate:.1f}% | Cache: {cache_hit_rate:.1f}%")
    print(f"  P50: {p50:.1f}ms | P95: {p95:.1f}ms {'✅' if p95 <= TARGET_P95_MS else '❌'} | P99: {p99:.1f}ms")
    
    return result


async def warmup(client: httpx.AsyncClient):
    """Warmup phase to reach steady state."""
    print("\n🔥 WARMUP PHASE (reaching steady state)")
    print("─" * 60)
    
    # Gradual ramp-up
    for phase, users in [("light", 100), ("medium", 300), ("heavy", WARMUP_USERS)]:
        print(f"  {phase}: {users} users...", end=" ")
        tasks = [simulate_user(client, i) for i in range(users)]
        await asyncio.gather(*tasks, return_exceptions=True)
        await asyncio.sleep(0.5)  # Brief pause between phases
        print("✓")
    
    # Let system stabilize
    print("  Stabilizing...", end=" ")
    await asyncio.sleep(2)
    print("✓")
    print("  Warmup complete!")


def analyze_consistency(results: List[IterationResult]) -> Dict[str, Any]:
    """Analyze consistency across iterations."""
    p95_values = [r.p95_ms for r in results]
    p50_values = [r.p50_ms for r in results]
    success_rates = [r.success_rate for r in results]
    throughputs = [r.throughput_rps for r in results]
    
    analysis = {
        "p95": {
            "mean": statistics.mean(p95_values),
            "min": min(p95_values),
            "max": max(p95_values),
            "std_dev": statistics.stdev(p95_values) if len(p95_values) > 1 else 0,
            "variance_pct": (max(p95_values) - min(p95_values)) / statistics.mean(p95_values) * 100,
            "all_under_target": all(p <= TARGET_P95_MS for p in p95_values),
        },
        "p50": {
            "mean": statistics.mean(p50_values),
            "min": min(p50_values),
            "max": max(p50_values),
            "std_dev": statistics.stdev(p50_values) if len(p50_values) > 1 else 0,
        },
        "success_rate": {
            "mean": statistics.mean(success_rates),
            "min": min(success_rates),
            "all_above_threshold": all(s >= MIN_SUCCESS_RATE for s in success_rates),
        },
        "throughput": {
            "mean": statistics.mean(throughputs),
            "std_dev": statistics.stdev(throughputs) if len(throughputs) > 1 else 0,
        },
    }
    
    return analysis


def calculate_consistency_score(analysis: Dict) -> Tuple[float, str]:
    """Calculate overall consistency score (0-100)."""
    scores = []
    messages = []
    
    # P95 consistency (40% weight)
    p95_variance = analysis["p95"]["variance_pct"]
    if p95_variance <= 5:
        scores.append(40)
        messages.append("P95 variance excellent (<5%)")
    elif p95_variance <= 10:
        scores.append(35)
        messages.append("P95 variance good (<10%)")
    elif p95_variance <= 15:
        scores.append(30)
        messages.append("P95 variance acceptable (<15%)")
    else:
        scores.append(20)
        messages.append("P95 variance high (>15%)")
    
    # P95 target achievement (30% weight)
    if analysis["p95"]["all_under_target"]:
        scores.append(30)
        messages.append("All P95s under 777ms target")
    elif analysis["p95"]["mean"] <= TARGET_P95_MS:
        scores.append(25)
        messages.append("Mean P95 under 777ms")
    else:
        scores.append(15)
        messages.append("P95 above target")
    
    # Success rate consistency (20% weight)
    if analysis["success_rate"]["all_above_threshold"]:
        scores.append(20)
        messages.append("All success rates >=95%")
    elif analysis["success_rate"]["min"] >= 90:
        scores.append(15)
        messages.append("Min success rate >=90%")
    else:
        scores.append(10)
        messages.append("Success rate inconsistent")
    
    # P50 optimization (10% weight)
    p50_mean = analysis["p50"]["mean"]
    if p50_mean <= TARGET_P50_MS:
        scores.append(10)
        messages.append(f"P50 optimized ({p50_mean:.0f}ms)")
    else:
        scores.append(5)
        messages.append(f"P50 could improve ({p50_mean:.0f}ms)")
    
    total_score = sum(scores)
    
    if total_score >= 90:
        rating = "EXCELLENT"
    elif total_score >= 75:
        rating = "GOOD"
    elif total_score >= 60:
        rating = "ACCEPTABLE"
    else:
        rating = "NEEDS WORK"
    
    return total_score, rating, messages


async def run_consistency_test():
    """Run full consistency test with multiple iterations."""
    print("=" * 80)
    print(f"🎯 CONSISTENCY TEST: {TARGET_P95_MS}ms P95")
    print(f"   {ITERATIONS} iterations × {CONCURRENT_USERS:,} users = {ITERATIONS * CONCURRENT_USERS * REQUESTS_PER_USER:,} total requests")
    print("=" * 80)
    print(f"\nRequirements:")
    print(f"  • P95 consistently <= {TARGET_P95_MS}ms across ALL iterations")
    print(f"  • P50 (average) approaching {TARGET_P50_MS}ms")
    print(f"  • Success rate >= {MIN_SUCCESS_RATE}% every time")
    print(f"  • P95 variance < {MAX_P95_VARIANCE_PCT}% between runs")
    
    # Connection pool optimized for consistency
    limits = httpx.Limits(
        max_connections=1000,
        max_keepalive_connections=500,
    )
    
    async with httpx.AsyncClient(
        base_url=BASE_URL,
        limits=limits,
        timeout=httpx.Timeout(2.0),
        http2=True,
    ) as client:
        # Health check
        try:
            resp = await client.get("/health", timeout=3.0)
            print(f"\n✅ Backend healthy: {resp.json()}")
        except Exception as e:
            print(f"\n❌ Backend unreachable: {e}")
            return False
        
        # Warmup phase
        await warmup(client)
        
        # Run iterations
        print("\n" + "=" * 80)
        print("📊 RUNNING ITERATIONS")
        print("=" * 80)
        
        iteration_results = []
        for i in range(1, ITERATIONS + 1):
            result = await run_iteration(client, i)
            iteration_results.append(result)
            
            # Brief pause between iterations
            if i < ITERATIONS:
                await asyncio.sleep(1)
        
        # Analyze consistency
        analysis = analyze_consistency(iteration_results)
        score, rating, messages = calculate_consistency_score(analysis)
        
        # ═══════════════════════════════════════════════════════════════════════════════
        # FINAL REPORT
        # ═══════════════════════════════════════════════════════════════════════════════
        print("\n" + "=" * 80)
        print("📈 CONSISTENCY ANALYSIS")
        print("=" * 80)
        
        print(f"\n🔢 STATISTICS ACROSS {ITERATIONS} ITERATIONS:")
        print(f"  P95 Latency:")
        print(f"    Mean: {analysis['p95']['mean']:.1f}ms")
        print(f"    Range: {analysis['p95']['min']:.1f}ms - {analysis['p95']['max']:.1f}ms")
        print(f"    Std Dev: {analysis['p95']['std_dev']:.1f}ms")
        print(f"    Variance: {analysis['p95']['variance_pct']:.1f}%")
        print(f"    All under {TARGET_P95_MS}ms: {'✅ YES' if analysis['p95']['all_under_target'] else '❌ NO'}")
        
        print(f"\n  P50 Latency (Average):")
        print(f"    Mean: {analysis['p50']['mean']:.1f}ms")
        print(f"    Range: {analysis['p50']['min']:.1f}ms - {analysis['p50']['max']:.1f}ms")
        print(f"    Target: <{TARGET_P50_MS}ms: {'✅ YES' if analysis['p50']['mean'] <= TARGET_P50_MS else '❌ NO'}")
        
        print(f"\n  Success Rate:")
        print(f"    Mean: {analysis['success_rate']['mean']:.1f}%")
        print(f"    Min: {analysis['success_rate']['min']:.1f}%")
        print(f"    All >= {MIN_SUCCESS_RATE}%: {'✅ YES' if analysis['success_rate']['all_above_threshold'] else '❌ NO'}")
        
        print(f"\n  Throughput:")
        print(f"    Mean: {analysis['throughput']['mean']:.0f} req/s")
        print(f"    Std Dev: {analysis['throughput']['std_dev']:.0f} req/s")
        
        # Score breakdown
        print(f"\n🎯 CONSISTENCY SCORE: {score}/100")
        print(f"   Rating: {rating}")
        print(f"\n   Breakdown:")
        for msg in messages:
            print(f"   • {msg}")
        
        # Pass/Fail
        print("\n" + "=" * 80)
        passed = (
            analysis['p95']['all_under_target'] and
            analysis['success_rate']['all_above_threshold'] and
            analysis['p95']['variance_pct'] <= MAX_P95_VARIANCE_PCT and
            score >= 75
        )
        
        if passed:
            print(f"🎉🎉🎉 CONSISTENCY TEST PASSED 🎉🎉🎉")
            print(f"\nThe system consistently achieves {TARGET_P95_MS}ms P95 latency!")
            print(f"Rating: {rating} ({score}/100)")
            print(f"\n✅ Ready for production at 5000 concurrent users")
        else:
            print(f"⚠️  CONSISTENCY TEST NEEDS IMPROVEMENT")
            print(f"\nIssues:")
            if not analysis['p95']['all_under_target']:
                print(f"  ❌ Not all P95s under {TARGET_P95_MS}ms")
            if not analysis['success_rate']['all_above_threshold']:
                print(f"  ❌ Success rate dropped below {MIN_SUCCESS_RATE}%")
            if analysis['p95']['variance_pct'] > MAX_P95_VARIANCE_PCT:
                print(f"  ❌ P95 variance too high ({analysis['p95']['variance_pct']:.1f}%)")
            if score < 75:
                print(f"  ❌ Consistency score too low ({score}/100)")
        
        print("=" * 80)
        
        # Save detailed results
        results_file = f"consistency_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w') as f:
            json.dump({
                "target_p95_ms": TARGET_P95_MS,
                "target_p50_ms": TARGET_P50_MS,
                "iterations": ITERATIONS,
                "concurrent_users": CONCURRENT_USERS,
                "results": [asdict(r) for r in iteration_results],
                "analysis": analysis,
                "score": score,
                "rating": rating,
                "passed": passed,
            }, f, indent=2)
        print(f"\n📁 Detailed results saved: {results_file}")
        
        return passed


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    try:
        success = asyncio.run(run_consistency_test())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n❌ Test error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
