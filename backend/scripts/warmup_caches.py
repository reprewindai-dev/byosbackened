"""
Pre-warm caches before load testing to ensure consistent performance.

Warms up:
- Database connection pool
- Redis connection pool  
- In-memory response caches
- JWT token validation cache
"""
import asyncio
import httpx
import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from core.config import get_settings
from core.redis_pool import get_redis, check_redis_health

settings = get_settings()

BASE_URL = "http://localhost:8000"


async def warmup_database_pool():
    """Warm up database connection pool."""
    print("🗄️  Warming up database connection pool...")
    
    from db.session import SessionLocal
    
    # Create and release connections to populate pool
    connections = []
    for i in range(20):  # Pre-create 20 connections
        try:
            db = SessionLocal()
            # Simple query to validate connection
            db.execute("SELECT 1")
            connections.append(db)
        except Exception as e:
            print(f"  Warning: Connection {i} failed: {e}")
    
    # Close them back to pool
    for db in connections:
        db.close()
    
    print(f"  ✅ {len(connections)} DB connections warmed")


def warmup_redis_pool():
    """Warm up Redis connection pool."""
    print("🔴 Warming up Redis connection pool...")
    
    try:
        r = get_redis()
        
        # Validate connection
        if r.ping():
            print("  ✅ Redis connection active")
        
        # Pre-populate with some warm data
        pipeline = r.pipeline()
        for i in range(10):
            pipeline.set(f"warmup:test:{i}", f"value_{i}", ex=60)
        pipeline.execute()
        
        print("  ✅ Redis pipeline warmed")
        
    except Exception as e:
        print(f"  ⚠️  Redis warmup failed: {e}")


async def warmup_http_endpoints():
    """Warm up HTTP endpoints and caches."""
    print("🌐 Warming up HTTP endpoints...")
    
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        # Health check
        try:
            resp = await client.get("/health")
            if resp.status_code == 200:
                print(f"  ✅ Health endpoint: {resp.json()}")
        except Exception as e:
            print(f"  ❌ Health check failed: {e}")
            return
        
        # Pre-warm cacheable endpoints (make requests to populate caches)
        warmup_paths = [
            "/api/v1/insights/summary",
            "/api/v1/autonomous/routing/stats",
            "/api/v1/suggestions",
            "/api/v1/budget",
        ]
        
        # Generate a test token
        import jwt
        payload = {
            "sub": "warmup@test.com",
            "user_id": "warmup-user",
            "workspace_id": "warmup-workspace",
            "exp": datetime.utcnow() + timedelta(hours=1),
        }
        token = jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)
        
        headers = {"Authorization": f"Bearer {token}"}
        
        for path in warmup_paths:
            try:
                resp = await client.get(path, headers=headers)
                if resp.status_code == 200:
                    cache_status = resp.headers.get("X-Cache", "N/A")
                    print(f"  ✅ {path}: cache={cache_status}")
                else:
                    print(f"  ⚠️  {path}: HTTP {resp.status_code}")
            except Exception as e:
                print(f"  ❌ {path}: {e}")
        
        # Make second request to verify caching works
        print("\n  Verifying caches (second request)...")
        for path in warmup_paths:
            try:
                resp = await client.get(path, headers=headers)
                cache_status = resp.headers.get("X-Cache", "N/A")
                print(f"  ✅ {path}: cache={cache_status}")
            except:
                pass


async def steady_state_check(duration_seconds: int = 10):
    """Verify steady state by making continuous requests."""
    print(f"\n📊 Steady-state verification ({duration_seconds}s)...")
    
    latencies = []
    
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=2.0) as client:
        start = asyncio.get_event_loop().time()
        
        while asyncio.get_event_loop().time() - start < duration_seconds:
            try:
                import time
                t0 = time.perf_counter()
                resp = await client.get("/health")
                latency = (time.perf_counter() - t0) * 1000
                latencies.append(latency)
            except:
                pass
            await asyncio.sleep(0.1)  # 10 req/s steady state
    
    if latencies:
        import statistics
        mean_lat = statistics.mean(latencies)
        std_dev = statistics.stdev(latencies) if len(latencies) > 1 else 0
        variance_pct = (std_dev / mean_lat * 100) if mean_lat > 0 else 0
        
        print(f"  Mean latency: {mean_lat:.1f}ms")
        print(f"  Std dev: {std_dev:.1f}ms")
        print(f"  Variance: {variance_pct:.1f}%")
        
        if variance_pct < 10:
            print("  ✅ System is in steady state (low variance)")
        else:
            print("  ⚠️  High variance detected - system still warming")


async def main():
    """Run full warmup sequence."""
    print("=" * 60)
    print("🔥 SYSTEM WARMUP - Preparing for Consistent Performance")
    print("=" * 60)
    print(f"Target: 777ms P95 consistency")
    print(f"Time: {datetime.now().isoformat()}")
    print("=" * 60)
    
    # 1. Database warmup
    await warmup_database_pool()
    
    # 2. Redis warmup
    warmup_redis_pool()
    
    # 3. HTTP endpoint warmup
    await warmup_http_endpoints()
    
    # 4. Steady state verification
    await steady_state_check(duration_seconds=10)
    
    print("\n" + "=" * 60)
    print("✅ WARMUP COMPLETE - System ready for load testing")
    print("=" * 60)
    print("\nNext steps:")
    print("  python tests/load/load_test_consistent_777ms.py")
    print("=" * 60)


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(main())
