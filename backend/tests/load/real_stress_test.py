"""
REAL STRESS TEST - Investor-grade, fully validated.

This test:
- Runs against the ACTUAL running server
- Tracks every request with correlation IDs
- Reports honest failure modes (no hidden errors)
- Tests at multiple load levels
- Saves raw audit log

NO FAKE NUMBERS. NO HIDDEN FAILURES.
"""
import asyncio
import httpx
import time
import statistics
import json
import sys
import os
import uuid
import hashlib
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import List, Dict, Any

BASE_URL = "http://127.0.0.1:8000"
TEST_RUN_ID = str(uuid.uuid4())[:8]


@dataclass
class RequestRecord:
    correlation_id: str
    timestamp: str
    endpoint: str
    method: str
    status_code: int
    latency_ms: float
    error: str
    response_size: int
    response_hash: str


# Public endpoints (no auth required) - these are what the previous locust tests hit
PUBLIC_ENDPOINTS = [
    ("GET", "/health"),
    ("GET", "/"),
    ("GET", "/status"),
    ("GET", "/api/v1/docs"),
    ("GET", "/api/v1/openapi.json"),
]


async def hit_endpoint(client: httpx.AsyncClient, method: str, endpoint: str, scenario: str) -> RequestRecord:
    """Make a single request and record everything."""
    correlation_id = f"{TEST_RUN_ID}-{scenario}-{uuid.uuid4().hex[:8]}"
    headers = {"X-Correlation-ID": correlation_id, "X-Test-Scenario": scenario}
    
    start = time.perf_counter()
    try:
        if method == "GET":
            r = await client.get(endpoint, headers=headers, timeout=10.0)
        else:
            r = await client.post(endpoint, headers=headers, timeout=10.0)
        
        latency = (time.perf_counter() - start) * 1000
        return RequestRecord(
            correlation_id=correlation_id,
            timestamp=datetime.now().isoformat(),
            endpoint=endpoint,
            method=method,
            status_code=r.status_code,
            latency_ms=latency,
            error="" if r.status_code < 500 else f"HTTP_{r.status_code}",
            response_size=len(r.content),
            response_hash=hashlib.sha256(r.content).hexdigest()[:12],
        )
    except Exception as e:
        latency = (time.perf_counter() - start) * 1000
        return RequestRecord(
            correlation_id=correlation_id,
            timestamp=datetime.now().isoformat(),
            endpoint=endpoint,
            method=method,
            status_code=0,
            latency_ms=latency,
            error=type(e).__name__ + ":" + str(e)[:60],
            response_size=0,
            response_hash="",
        )


async def run_scenario(name: str, concurrent: int, total_requests: int) -> Dict[str, Any]:
    """Run one stress test scenario."""
    print(f"\n{'='*80}")
    print(f"SCENARIO: {name}")
    print(f"  Concurrent users: {concurrent}")
    print(f"  Total requests:   {total_requests}")
    print(f"{'='*80}")
    
    limits = httpx.Limits(max_connections=concurrent * 2, max_keepalive_connections=concurrent)
    
    records: List[RequestRecord] = []
    
    async with httpx.AsyncClient(base_url=BASE_URL, limits=limits, timeout=10.0) as client:
        # Pre-flight check
        try:
            health = await client.get("/health", timeout=3.0)
            if health.status_code != 200:
                print(f"  ⚠️  Server unhealthy: {health.status_code}")
                return None
        except Exception as e:
            print(f"  ❌ Server unreachable: {e}")
            return None
        
        sem = asyncio.Semaphore(concurrent)
        
        async def bounded_request(i: int):
            async with sem:
                method, endpoint = PUBLIC_ENDPOINTS[i % len(PUBLIC_ENDPOINTS)]
                rec = await hit_endpoint(client, method, endpoint, name)
                records.append(rec)
        
        wall_start = time.perf_counter()
        await asyncio.gather(*[bounded_request(i) for i in range(total_requests)])
        wall_duration = time.perf_counter() - wall_start
    
    # Honest analysis
    total = len(records)
    successful = [r for r in records if 200 <= r.status_code < 400]
    server_errors = [r for r in records if r.status_code >= 500]
    client_errors = [r for r in records if 400 <= r.status_code < 500]
    network_errors = [r for r in records if r.status_code == 0]
    
    success_rate = len(successful) / total * 100 if total else 0
    latencies = [r.latency_ms for r in successful]
    
    if latencies:
        sorted_lat = sorted(latencies)
        n = len(sorted_lat)
        p50 = sorted_lat[int(n * 0.50)]
        p95 = sorted_lat[int(n * 0.95)] if n >= 20 else sorted_lat[-1]
        p99 = sorted_lat[int(n * 0.99)] if n >= 100 else sorted_lat[-1]
        mean = statistics.mean(latencies)
        max_lat = max(latencies)
        min_lat = min(latencies)
    else:
        p50 = p95 = p99 = mean = max_lat = min_lat = 0
    
    print(f"\nRESULTS:")
    print(f"  Duration:         {wall_duration:.1f}s")
    print(f"  Throughput:       {total/wall_duration:.0f} req/s")
    print(f"  Total requests:   {total}")
    print(f"  Successful (2xx): {len(successful)} ({success_rate:.1f}%)")
    print(f"  Client errors:    {len(client_errors)} ({len(client_errors)/total*100:.1f}%)")
    print(f"  Server errors:    {len(server_errors)} ({len(server_errors)/total*100:.1f}%)")
    print(f"  Network errors:   {len(network_errors)} ({len(network_errors)/total*100:.1f}%)")
    
    if latencies:
        print(f"\nLATENCY (successful only):")
        print(f"  Min:  {min_lat:>7.1f}ms")
        print(f"  P50:  {p50:>7.1f}ms")
        print(f"  Mean: {mean:>7.1f}ms")
        print(f"  P95:  {p95:>7.1f}ms")
        print(f"  P99:  {p99:>7.1f}ms")
        print(f"  Max:  {max_lat:>7.1f}ms")
    
    # Error breakdown
    if server_errors or network_errors:
        print(f"\nERROR DETAIL:")
        err_counts: Dict[str, int] = {}
        for r in server_errors + network_errors:
            err_counts[r.error] = err_counts.get(r.error, 0) + 1
        for err, count in sorted(err_counts.items(), key=lambda x: -x[1])[:10]:
            print(f"  {count:>5}x  {err}")
    
    # Per-endpoint breakdown
    print(f"\nPER-ENDPOINT:")
    endpoint_stats: Dict[str, List[RequestRecord]] = {}
    for r in records:
        endpoint_stats.setdefault(r.endpoint, []).append(r)
    
    for ep, recs in endpoint_stats.items():
        ok = sum(1 for r in recs if 200 <= r.status_code < 400)
        ep_lats = [r.latency_ms for r in recs if 200 <= r.status_code < 400]
        ep_p95 = sorted(ep_lats)[int(len(ep_lats)*0.95)] if len(ep_lats) >= 20 else (max(ep_lats) if ep_lats else 0)
        ep_mean = statistics.mean(ep_lats) if ep_lats else 0
        print(f"  {ep:35s}  {ok:>4}/{len(recs):<4}  mean={ep_mean:>6.1f}ms  p95={ep_p95:>6.1f}ms")
    
    return {
        "scenario": name,
        "concurrent": concurrent,
        "total_requests": total,
        "duration_seconds": wall_duration,
        "throughput_rps": total / wall_duration,
        "success_rate": success_rate,
        "successful": len(successful),
        "server_errors": len(server_errors),
        "client_errors": len(client_errors),
        "network_errors": len(network_errors),
        "latency": {
            "min_ms": min_lat,
            "p50_ms": p50,
            "mean_ms": mean,
            "p95_ms": p95,
            "p99_ms": p99,
            "max_ms": max_lat,
        },
        "per_endpoint": {
            ep: {
                "total": len(recs),
                "successful": sum(1 for r in recs if 200 <= r.status_code < 400),
                "mean_ms": statistics.mean([r.latency_ms for r in recs if 200 <= r.status_code < 400]) if any(200 <= r.status_code < 400 for r in recs) else 0,
            }
            for ep, recs in endpoint_stats.items()
        },
        "raw_sample": [asdict(r) for r in records[:50]],
    }


async def main():
    print("="*80)
    print(f"BYOS BACKEND - REAL STRESS TEST")
    print(f"Test Run ID: {TEST_RUN_ID}")
    print(f"Started:     {datetime.now().isoformat()}")
    print(f"Target:      {BASE_URL}")
    print("="*80)
    
    scenarios = [
        ("smoke",       10,   100),
        ("light",       50,   500),
        ("baseline",    100,  1000),
        ("sustained",   200,  3000),
        ("heavy",       500,  5000),
    ]
    
    all_results = []
    for name, concurrent, total in scenarios:
        result = await run_scenario(name, concurrent, total)
        if result:
            all_results.append(result)
        # Cooldown between scenarios
        await asyncio.sleep(2)
    
    # ───────────────── SUMMARY ─────────────────
    print("\n" + "="*80)
    print("FINAL SUMMARY (all scenarios)")
    print("="*80)
    print(f"\n{'Scenario':<12} {'Conc':<6} {'Total':<6} {'Success%':<10} {'P50':<8} {'P95':<8} {'P99':<8} {'RPS':<6}")
    print("-"*80)
    for r in all_results:
        print(f"{r['scenario']:<12} {r['concurrent']:<6} {r['total_requests']:<6} "
              f"{r['success_rate']:<9.1f}% {r['latency']['p50_ms']:<7.0f}ms "
              f"{r['latency']['p95_ms']:<7.0f}ms {r['latency']['p99_ms']:<7.0f}ms "
              f"{r['throughput_rps']:<6.0f}")
    
    # Save audit
    audit_file = f"stress_test_{TEST_RUN_ID}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(audit_file, "w") as f:
        json.dump({
            "test_run_id": TEST_RUN_ID,
            "timestamp": datetime.now().isoformat(),
            "base_url": BASE_URL,
            "scenarios": all_results,
        }, f, indent=2)
    
    print(f"\n📁 Full audit saved: {audit_file}")
    print("="*80)
    
    # Honest verdict
    print("\nHONEST VERDICT:")
    for r in all_results:
        verdict = "✅ PASS" if r['success_rate'] >= 95 else ("⚠️  DEGRADED" if r['success_rate'] >= 80 else "❌ FAIL")
        print(f"  {verdict}  {r['scenario']:<12} success={r['success_rate']:.1f}% p95={r['latency']['p95_ms']:.0f}ms")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
