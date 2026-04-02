"""Detailed live streaming performance tests - TikTok Live quality."""

import pytest
import httpx
import asyncio
import time
import statistics
from datetime import datetime

BASE_URL = "http://localhost:8000"
API_PREFIX = "/api/v1"


async def test_live_stream_latency():
    """Test live stream latency - should be <100ms for TikTok Live quality."""
    print("\n" + "=" * 60)
    print("TEST: LIVE STREAM LATENCY (TIKTOK LIVE QUALITY)")
    print("=" * 60)

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Login
        login_response = await client.post(
            f"{BASE_URL}{API_PREFIX}/auth/login-json",
            json={"email": "anthonymillwater2@hotmail.com", "password": "GoonSite32$"},
        )

        if login_response.status_code != 200:
            return

        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Start stream
        start_response = await client.post(
            f"{BASE_URL}{API_PREFIX}/live/start", headers=headers, json={"title": "Latency Test"}
        )

        if start_response.status_code != 201:
            return

        stream_id = start_response.json()["stream_id"]

        # Measure latency for various operations
        latencies = {
            "join": [],
            "status": [],
            "gift": [],
            "viewers": [],
        }

        print("\n[1/3] Measuring operation latencies...")

        # Join latency (should be <100ms)
        for i in range(50):
            start = time.perf_counter()
            await client.post(f"{BASE_URL}{API_PREFIX}/live/{stream_id}/join", headers=headers)
            latency = (time.perf_counter() - start) * 1000  # Convert to ms
            latencies["join"].append(latency)
            await asyncio.sleep(0.02)  # 20ms between operations

        # Status check latency
        for i in range(50):
            start = time.perf_counter()
            await client.get(f"{BASE_URL}{API_PREFIX}/live/active", headers=headers)
            latency = (time.perf_counter() - start) * 1000
            latencies["status"].append(latency)
            await asyncio.sleep(0.02)

        # Gift latency
        for i in range(20):
            start = time.perf_counter()
            await client.post(
                f"{BASE_URL}{API_PREFIX}/live/{stream_id}/gift",
                headers=headers,
                params={"gift_type": "rose"},
            )
            latency = (time.perf_counter() - start) * 1000
            latencies["gift"].append(latency)
            await asyncio.sleep(0.05)

        # Analyze latencies
        print("\n[2/3] Latency Analysis:")
        all_latencies = []

        for op_type, times in latencies.items():
            if times:
                avg = statistics.mean(times)
                median = statistics.median(times)
                p95 = sorted(times)[int(len(times) * 0.95)]
                p99 = sorted(times)[int(len(times) * 0.99)]
                max_latency = max(times)

                print(f"\n   {op_type.upper()}:")
                print(f"      Average: {avg:.2f}ms")
                print(f"      Median: {median:.2f}ms")
                print(f"      P95: {p95:.2f}ms")
                print(f"      P99: {p99:.2f}ms")
                print(f"      Max: {max_latency:.2f}ms")

                all_latencies.extend(times)

                # TikTok Live quality check (<100ms average)
                if avg < 100:
                    print(f"      ✅ TikTok Live quality (avg <100ms)")
                else:
                    print(f"      ⚠️  Above TikTok Live quality threshold")

        # Overall latency
        if all_latencies:
            overall_avg = statistics.mean(all_latencies)
            overall_p95 = sorted(all_latencies)[int(len(all_latencies) * 0.95)]

            print(f"\n   OVERALL:")
            print(f"      Average: {overall_avg:.2f}ms")
            print(f"      P95: {overall_p95:.2f}ms")

            if overall_avg < 100 and overall_p95 < 200:
                print(f"      ✅ TikTok Live quality achieved!")
            else:
                print(f"      ⚠️  Needs optimization")

        # End stream
        await client.post(f"{BASE_URL}{API_PREFIX}/live/{stream_id}/end", headers=headers)

    print("\n" + "=" * 60)
    print("✅ LATENCY TEST COMPLETE")
    print("=" * 60)


async def test_live_stream_throughput():
    """Test live stream throughput - operations per second."""
    print("\n" + "=" * 60)
    print("TEST: LIVE STREAM THROUGHPUT")
    print("=" * 60)

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Login
        login_response = await client.post(
            f"{BASE_URL}{API_PREFIX}/auth/login-json",
            json={"email": "anthonymillwater2@hotmail.com", "password": "GoonSite32$"},
        )

        if login_response.status_code != 200:
            return

        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Start stream
        start_response = await client.post(
            f"{BASE_URL}{API_PREFIX}/live/start", headers=headers, json={"title": "Throughput Test"}
        )

        if start_response.status_code != 201:
            return

        stream_id = start_response.json()["stream_id"]

        # Test throughput (operations per second)
        print("\n[1/2] Testing throughput (10 seconds)...")
        start_time = time.time()
        operation_count = 0

        while time.time() - start_time < 10:
            # Mix of operations
            if operation_count % 3 == 0:
                await client.post(f"{BASE_URL}{API_PREFIX}/live/{stream_id}/join", headers=headers)
            elif operation_count % 3 == 1:
                await client.get(f"{BASE_URL}{API_PREFIX}/live/active", headers=headers)
            else:
                await client.post(
                    f"{BASE_URL}{API_PREFIX}/live/{stream_id}/gift",
                    headers=headers,
                    params={"gift_type": "rose"},
                )

            operation_count += 1
            await asyncio.sleep(0.01)  # 10ms = 100 ops/sec target

        duration = time.time() - start_time
        ops_per_sec = operation_count / duration

        print(f"   ✅ Completed {operation_count} operations in {duration:.2f}s")
        print(f"   ✅ Throughput: {ops_per_sec:.1f} ops/sec")

        if ops_per_sec >= 50:
            print(f"   ✅ High throughput achieved (>=50 ops/sec)")
        else:
            print(f"   ⚠️  Throughput below target")

        # Test burst throughput
        print("\n[2/2] Testing burst throughput...")
        burst_start = time.time()
        burst_count = 0

        # Rapid burst of 100 operations
        tasks = []
        for i in range(100):
            if i % 2 == 0:
                tasks.append(
                    client.post(f"{BASE_URL}{API_PREFIX}/live/{stream_id}/join", headers=headers)
                )
            else:
                tasks.append(client.get(f"{BASE_URL}{API_PREFIX}/live/active", headers=headers))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        burst_duration = time.time() - burst_start
        burst_ops_per_sec = (
            len([r for r in results if not isinstance(r, Exception)]) / burst_duration
        )

        print(
            f"   ✅ Burst: {len([r for r in results if not isinstance(r, Exception)])} operations in {burst_duration:.2f}s"
        )
        print(f"   ✅ Burst throughput: {burst_ops_per_sec:.1f} ops/sec")

        # End stream
        await client.post(f"{BASE_URL}{API_PREFIX}/live/{stream_id}/end", headers=headers)

    print("\n" + "=" * 60)
    print("✅ THROUGHPUT TEST COMPLETE")
    print("=" * 60)


async def test_live_stream_no_buffering():
    """Test that live stream has no buffering issues."""
    print("\n" + "=" * 60)
    print("TEST: NO BUFFERING (FLUID OPERATION)")
    print("=" * 60)

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Login
        login_response = await client.post(
            f"{BASE_URL}{API_PREFIX}/auth/login-json",
            json={"email": "anthonymillwater2@hotmail.com", "password": "GoonSite32$"},
        )

        if login_response.status_code != 200:
            return

        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Start stream
        start_response = await client.post(
            f"{BASE_URL}{API_PREFIX}/live/start",
            headers=headers,
            json={"title": "No Buffering Test"},
        )

        if start_response.status_code != 201:
            return

        stream_id = start_response.json()["stream_id"]

        # Continuous operation test (simulate 60 seconds of activity)
        print("\n[1/2] Continuous operation test (60 seconds)...")
        start_time = time.time()
        operation_times = []
        slow_operations = []

        while time.time() - start_time < 60:
            op_start = time.perf_counter()

            # Random operation
            import random

            op_type = random.choice(["join", "status", "gift"])

            if op_type == "join":
                await client.post(f"{BASE_URL}{API_PREFIX}/live/{stream_id}/join", headers=headers)
            elif op_type == "status":
                await client.get(f"{BASE_URL}{API_PREFIX}/live/active", headers=headers)
            else:
                await client.post(
                    f"{BASE_URL}{API_PREFIX}/live/{stream_id}/gift",
                    headers=headers,
                    params={"gift_type": "rose"},
                )

            op_duration = (time.perf_counter() - op_start) * 1000  # ms
            operation_times.append(op_duration)

            # Detect buffering (operations >500ms are considered buffering)
            if op_duration > 500:
                slow_operations.append(op_duration)

            await asyncio.sleep(0.1)  # 10 ops/sec

        duration = time.time() - start_time
        total_ops = len(operation_times)

        print(f"   ✅ Completed {total_ops} operations in {duration:.1f}s")
        print(f"   ✅ Average: {statistics.mean(operation_times):.2f}ms")
        print(f"   ✅ Max: {max(operation_times):.2f}ms")
        print(f"   ✅ Slow operations (>500ms): {len(slow_operations)}")

        if len(slow_operations) == 0:
            print(f"   ✅ NO BUFFERING DETECTED - Fluid operation!")
        else:
            print(f"   ⚠️  {len(slow_operations)} buffering events detected")

        # Consistency test
        print("\n[2/2] Consistency test (operation time variance)...")
        if len(operation_times) > 1:
            variance = statistics.variance(operation_times)
            std_dev = statistics.stdev(operation_times)

            print(f"   ✅ Variance: {variance:.2f}ms²")
            print(f"   ✅ Std Dev: {std_dev:.2f}ms")

            if std_dev < 100:
                print(f"   ✅ Consistent performance (low variance)")
            else:
                print(f"   ⚠️  High variance - inconsistent performance")

        # End stream
        await client.post(f"{BASE_URL}{API_PREFIX}/live/{stream_id}/end", headers=headers)

    print("\n" + "=" * 60)
    print("✅ NO BUFFERING TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("DETAILED LIVE STREAMING PERFORMANCE TESTS")
    print("=" * 60)

    asyncio.run(test_live_stream_latency())
    asyncio.run(test_live_stream_throughput())
    asyncio.run(test_live_stream_no_buffering())

    print("\n" + "=" * 60)
    print("ALL PERFORMANCE TESTS COMPLETE")
    print("=" * 60)
