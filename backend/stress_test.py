#!/usr/bin/env python3
"""Stress test auth and support endpoints."""
import asyncio
import httpx
import time
import random
import string
from datetime import datetime

BASE_URL = "http://localhost:8001"
CONCURRENT = 50
REQUESTS_PER_CLIENT = 20

def random_email():
    return f"user_{''.join(random.choices(string.ascii_lowercase, k=8))}@test.com"

def random_password():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=12))

async def client_worker(client_id: int, results: list):
    async with httpx.AsyncClient(timeout=30.0) as client:
        for i in range(REQUESTS_PER_CLIENT):
            start = time.time()
            try:
                # Mix of register attempts and support bot queries
                if random.random() < 0.3:
                    # Register attempt (will fail due to weak password test)
                    payload = {
                        "email": random_email(),
                        "password": random_password(),
                        "workspace_name": f"Test Workspace {client_id}-{i}",
                    }
                    resp = await client.post(f"{BASE_URL}/api/v1/auth/register", json=payload)
                    status = resp.status_code
                    success = status == 201
                else:
                    # Support bot query
                    queries = [
                        "What plans do you offer?",
                        "How do I reset my API key?",
                        "What's the pricing for Pro plan?",
                        "I got a 401 error, help",
                        "How does token billing work?",
                        "What models are supported?",
                        "How do I upgrade my plan?",
                        "What's the difference between Sovereign and Essential marketplace?",
                    ]
                    resp = await client.post(
                        f"{BASE_URL}/api/v1/support/chat",
                        json={"message": random.choice(queries)}
                    )
                    status = resp.status_code
                    success = status == 200
                
                elapsed = time.time() - start
                results.append({
                    "client": client_id,
                    "request": i,
                    "status": status,
                    "success": success,
                    "latency": elapsed,
                    "timestamp": datetime.utcnow().isoformat(),
                })
            except Exception as e:
                elapsed = time.time() - start
                results.append({
                    "client": client_id,
                    "request": i,
                    "status": 0,
                    "success": False,
                    "latency": elapsed,
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat(),
                })

async def main():
    print(f"🚀 Stress test: {CONCURRENT} clients × {REQUESTS_PER_CLIENT} requests = {CONCURRENT * REQUESTS_PER_CLIENT} total")
    print(f"Target: {BASE_URL}")
    print("-" * 60)
    
    start_time = time.time()
    results = []
    
    tasks = [client_worker(i, results) for i in range(CONCURRENT)]
    await asyncio.gather(*tasks)
    
    total_time = time.time() - start_time
    total_requests = len(results)
    successes = sum(1 for r in results if r["success"])
    failures = total_requests - successes
    
    latencies = [r["latency"] for r in results]
    avg_latency = sum(latencies) / len(latencies)
    p95_latency = sorted(latencies)[int(0.95 * len(latencies))]
    
    # Status code breakdown
    status_counts = {}
    for r in results:
        status_counts[r["status"]] = status_counts.get(r["status"], 0) + 1
    
    print(f"\n📊 RESULTS ({total_time:.2f}s total)")
    print(f"  Requests: {total_requests} ({total_requests/total_time:.1f} req/s)")
    print(f"  Success: {successes} ({100*successes/total_requests:.1f}%)")
    print(f"  Failures: {failures} ({100*failures/total_requests:.1f}%)")
    print(f"  Latency: avg {avg_latency*1000:.0f}ms, p95 {p95_latency*1000:.0f}ms")
    print(f"\n🔍 STATUS CODES")
    for code, count in sorted(status_counts.items()):
        print(f"  {code}: {count}")
    
    # Show some errors
    errors = [r for r in results if not r["success"] and "error" in r]
    if errors:
        print(f"\n❌ SAMPLE ERRORS (showing first 3)")
        for e in errors[:3]:
            print(f"  Client {e['client']}: {e['error']}")
    
    print(f"\n✅ Stress test complete")
    
    # Basic health check
    try:
        health = await httpx.AsyncClient().get(f"{BASE_URL}/health")
        print(f"🏥 Health check: {health.status_code}")
    except Exception as e:
        print(f"🏥 Health check failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
