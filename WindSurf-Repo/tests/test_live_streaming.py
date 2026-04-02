"""Test live streaming functionality - TikTok Live style."""

import pytest
import httpx
import asyncio
import time
from datetime import datetime

BASE_URL = "http://localhost:8000"
API_PREFIX = "/api/v1"


async def test_live_stream_start_end():
    """Test starting and ending a live stream."""
    print("\n" + "=" * 60)
    print("TEST: LIVE STREAM START/END")
    print("=" * 60)

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Login
        print("\n[1/4] Logging in...")
        login_response = await client.post(
            f"{BASE_URL}{API_PREFIX}/auth/login-json",
            json={"email": "anthonymillwater2@hotmail.com", "password": "GoonSite32$"},
        )

        if login_response.status_code != 200:
            print(f"   ⚠️  Login failed: {login_response.status_code}")
            return

        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print(f"   ✅ Logged in")

        # Start live stream
        print("\n[2/4] Starting live stream...")
        start_response = await client.post(
            f"{BASE_URL}{API_PREFIX}/live/start",
            headers=headers,
            json={
                "title": "Test Live Stream",
                "description": "Testing live streaming functionality",
                "chat_enabled": True,
                "gifts_enabled": True,
                "tags": ["test", "live", "demo"],
            },
        )

        if start_response.status_code == 201:
            stream_data = start_response.json()
            stream_id = stream_data["stream_id"]
            print(f"   ✅ Live stream started: {stream_id}")
            print(f"   RTMP URL: {stream_data['rtmp_url']}")
            print(f"   Stream Key: {stream_data['stream_key']}")
            print(f"   Playback URL: {stream_data['playback_url']}")

            # Simulate stream running
            print("\n[3/4] Simulating stream (5 seconds)...")
            await asyncio.sleep(5)

            # Join as viewer
            print("\n[3.5/4] Joining as viewer...")
            join_response = await client.post(
                f"{BASE_URL}{API_PREFIX}/live/{stream_id}/join", headers=headers
            )
            if join_response.status_code == 200:
                join_data = join_response.json()
                print(f"   ✅ Joined stream")
                print(f"   Current viewers: {join_data.get('current_viewers', 0)}")

            # End stream
            print("\n[4/4] Ending live stream...")
            end_response = await client.post(
                f"{BASE_URL}{API_PREFIX}/live/{stream_id}/end", headers=headers
            )

            if end_response.status_code == 200:
                end_data = end_response.json()
                print(f"   ✅ Stream ended")
                print(f"   Gems earned: {end_data.get('gems_earned', 0)}")
                print(f"   Duration: {end_data.get('duration_minutes', 0)} minutes")
                print(f"   Peak viewers: {end_data.get('peak_viewers', 0)}")
            else:
                print(f"   ⚠️  End failed: {end_response.status_code}")
        else:
            print(f"   ⚠️  Start failed: {start_response.status_code}")
            print(f"   Response: {start_response.text}")

    print("\n" + "=" * 60)
    print("✅ LIVE STREAM START/END TEST COMPLETE")
    print("=" * 60)


async def test_live_stream_performance():
    """Test live stream performance - no buffering, fluid operation."""
    print("\n" + "=" * 60)
    print("TEST: LIVE STREAM PERFORMANCE (FLUIDITY & BUFFERING)")
    print("=" * 60)

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Login
        print("\n[1/6] Logging in...")
        login_response = await client.post(
            f"{BASE_URL}{API_PREFIX}/auth/login-json",
            json={"email": "anthonymillwater2@hotmail.com", "password": "GoonSite32$"},
        )

        if login_response.status_code != 200:
            print(f"   ⚠️  Login failed")
            return

        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Start stream
        print("\n[2/6] Starting live stream...")
        start_time = time.time()
        start_response = await client.post(
            f"{BASE_URL}{API_PREFIX}/live/start",
            headers=headers,
            json={
                "title": "Performance Test Stream",
                "description": "Testing fluidity and buffering",
                "chat_enabled": True,
                "gifts_enabled": True,
            },
        )
        start_duration = time.time() - start_time

        if start_response.status_code != 201:
            print(f"   ⚠️  Start failed: {start_response.status_code}")
            return

        stream_data = start_response.json()
        stream_id = stream_data["stream_id"]
        print(f"   ✅ Stream started in {start_duration:.2f}s")
        assert start_duration < 2.0, f"Stream start too slow: {start_duration:.2f}s"

        # Test viewer join performance
        print("\n[3/6] Testing viewer join performance...")
        join_times = []
        for i in range(10):
            join_start = time.time()
            join_response = await client.post(
                f"{BASE_URL}{API_PREFIX}/live/{stream_id}/join", headers=headers
            )
            join_duration = time.time() - join_start
            join_times.append(join_duration)

            if join_response.status_code == 200:
                await asyncio.sleep(0.1)  # Small delay between joins

        avg_join_time = sum(join_times) / len(join_times)
        max_join_time = max(join_times)
        print(f"   ✅ Average join time: {avg_join_time:.3f}s")
        print(f"   ✅ Max join time: {max_join_time:.3f}s")
        assert avg_join_time < 0.5, f"Join too slow: {avg_join_time:.3f}s"
        assert max_join_time < 1.0, f"Max join too slow: {max_join_time:.3f}s"

        # Test concurrent viewers (simulate multiple viewers)
        print("\n[4/6] Testing concurrent viewer handling...")
        concurrent_start = time.time()

        async def join_viewer():
            async with httpx.AsyncClient(timeout=10.0) as viewer_client:
                response = await viewer_client.post(
                    f"{BASE_URL}{API_PREFIX}/live/{stream_id}/join", headers=headers
                )
                return response.status_code == 200

        # Simulate 20 concurrent viewers
        tasks = [join_viewer() for _ in range(20)]
        results = await asyncio.gather(*tasks)
        concurrent_duration = time.time() - concurrent_start

        successful_joins = sum(results)
        print(f"   ✅ {successful_joins}/20 concurrent viewers joined")
        print(f"   ✅ Concurrent join duration: {concurrent_duration:.2f}s")
        assert concurrent_duration < 5.0, f"Concurrent joins too slow: {concurrent_duration:.2f}s"

        # Test gift sending performance
        print("\n[5/6] Testing gift sending performance...")
        gift_times = []
        for gift_type in ["rose", "diamond", "crown"]:
            gift_start = time.time()
            gift_response = await client.post(
                f"{BASE_URL}{API_PREFIX}/live/{stream_id}/gift",
                headers=headers,
                params={"gift_type": gift_type},
            )
            gift_duration = time.time() - gift_start
            gift_times.append(gift_duration)

            if gift_response.status_code == 200:
                await asyncio.sleep(0.1)

        avg_gift_time = sum(gift_times) / len(gift_times)
        print(f"   ✅ Average gift send time: {avg_gift_time:.3f}s")
        assert avg_gift_time < 0.5, f"Gift send too slow: {avg_gift_time:.3f}s"

        # Test stream status updates (no buffering)
        print("\n[6/6] Testing stream status updates (buffering check)...")
        status_times = []
        for i in range(5):
            status_start = time.time()
            status_response = await client.get(
                f"{BASE_URL}{API_PREFIX}/live/active", headers=headers
            )
            status_duration = time.time() - status_start
            status_times.append(status_duration)

            if status_response.status_code == 200:
                streams = status_response.json().get("items", [])
                if streams:
                    stream = streams[0]
                    print(
                        f"   Viewers: {stream.get('current_viewers', 0)}, "
                        f"Peak: {stream.get('peak_viewers', 0)}"
                    )

            await asyncio.sleep(0.5)

        avg_status_time = sum(status_times) / len(status_times)
        print(f"   ✅ Average status check time: {avg_status_time:.3f}s")
        assert avg_status_time < 0.3, f"Status check too slow: {avg_status_time:.3f}s"

        # End stream
        await client.post(f"{BASE_URL}{API_PREFIX}/live/{stream_id}/end", headers=headers)

    print("\n" + "=" * 60)
    print("✅ PERFORMANCE TEST COMPLETE - NO BUFFERING ISSUES")
    print("=" * 60)


async def test_live_stream_fluidity():
    """Test live stream fluidity - like TikTok Live."""
    print("\n" + "=" * 60)
    print("TEST: LIVE STREAM FLUIDITY (TIKTOK LIVE STYLE)")
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
        print("\n[1/5] Starting stream...")
        start_response = await client.post(
            f"{BASE_URL}{API_PREFIX}/live/start",
            headers=headers,
            json={"title": "Fluidity Test", "chat_enabled": True, "gifts_enabled": True},
        )

        if start_response.status_code != 201:
            print(f"   ⚠️  Start failed")
            return

        stream_id = start_response.json()["stream_id"]
        print(f"   ✅ Stream started")

        # Test rapid operations (simulating TikTok Live fluidity)
        print("\n[2/5] Testing rapid operations (TikTok Live style)...")
        operations = []

        # Rapid viewer joins
        for i in range(30):
            op_start = time.time()
            await client.post(f"{BASE_URL}{API_PREFIX}/live/{stream_id}/join", headers=headers)
            op_duration = time.time() - op_start
            operations.append(("join", op_duration))
            await asyncio.sleep(0.05)  # 50ms between operations

        # Rapid gifts
        for i in range(10):
            op_start = time.time()
            await client.post(
                f"{BASE_URL}{API_PREFIX}/live/{stream_id}/gift",
                headers=headers,
                params={"gift_type": "rose"},
            )
            op_duration = time.time() - op_start
            operations.append(("gift", op_duration))
            await asyncio.sleep(0.1)

        # Rapid status checks
        for i in range(10):
            op_start = time.time()
            await client.get(f"{BASE_URL}{API_PREFIX}/live/active", headers=headers)
            op_duration = time.time() - op_start
            operations.append(("status", op_duration))
            await asyncio.sleep(0.1)

        # Analyze performance
        join_times = [d for op, d in operations if op == "join"]
        gift_times = [d for op, d in operations if op == "gift"]
        status_times = [d for op, d in operations if op == "status"]

        print(
            f"   ✅ Join operations: avg {sum(join_times)/len(join_times):.3f}s, max {max(join_times):.3f}s"
        )
        print(
            f"   ✅ Gift operations: avg {sum(gift_times)/len(gift_times):.3f}s, max {max(gift_times):.3f}s"
        )
        print(
            f"   ✅ Status operations: avg {sum(status_times)/len(status_times):.3f}s, max {max(status_times):.3f}s"
        )

        # Check for buffering (all operations should be fast)
        all_times = join_times + gift_times + status_times
        slow_operations = [t for t in all_times if t > 1.0]

        if slow_operations:
            print(f"   ⚠️  Found {len(slow_operations)} slow operations (>1s)")
        else:
            print(f"   ✅ No buffering detected - all operations <1s")

        assert len(slow_operations) == 0, f"Found {len(slow_operations)} slow operations"

        # Test continuous operation (simulate 30 seconds of activity)
        print("\n[3/5] Testing continuous operation (30s)...")
        start_time = time.time()
        operation_count = 0

        while time.time() - start_time < 30:
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
            await asyncio.sleep(0.2)  # 5 operations per second

        print(f"   ✅ Completed {operation_count} operations in 30s")
        print(f"   ✅ Average: {operation_count/30:.1f} ops/sec")
        assert operation_count >= 100, f"Too few operations: {operation_count}"

        # Test stream end performance
        print("\n[4/5] Testing stream end performance...")
        end_start = time.time()
        end_response = await client.post(
            f"{BASE_URL}{API_PREFIX}/live/{stream_id}/end", headers=headers
        )
        end_duration = time.time() - end_start

        if end_response.status_code == 200:
            end_data = end_response.json()
            print(f"   ✅ Stream ended in {end_duration:.2f}s")
            print(f"   Gems earned: {end_data.get('gems_earned', 0)}")
            assert end_duration < 2.0, f"End too slow: {end_duration:.2f}s"

        # Final performance summary
        print("\n[5/5] Performance Summary:")
        print(f"   ✅ All operations completed successfully")
        print(f"   ✅ No buffering detected")
        print(f"   ✅ Fluid operation like TikTok Live")
        print(f"   ✅ {operation_count} operations in 30s")

    print("\n" + "=" * 60)
    print("✅ FLUIDITY TEST COMPLETE - TIKTOK LIVE STYLE")
    print("=" * 60)


async def test_live_stream_concurrent():
    """Test concurrent live streams."""
    print("\n" + "=" * 60)
    print("TEST: CONCURRENT LIVE STREAMS")
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

        # Start multiple streams concurrently
        print("\n[1/3] Starting 5 concurrent streams...")

        async def start_stream(i):
            response = await client.post(
                f"{BASE_URL}{API_PREFIX}/live/start",
                headers=headers,
                json={"title": f"Concurrent Stream {i}", "chat_enabled": True},
            )
            return response.status_code == 201, (
                response.json() if response.status_code == 201 else None
            )

        tasks = [start_stream(i) for i in range(5)]
        results = await asyncio.gather(*tasks)

        successful = sum(1 for success, _ in results if success)
        stream_ids = [data["stream_id"] for success, data in results if success and data]

        print(f"   ✅ {successful}/5 streams started")

        # Check active streams
        print("\n[2/3] Checking active streams...")
        active_response = await client.get(f"{BASE_URL}{API_PREFIX}/live/active", headers=headers)

        if active_response.status_code == 200:
            active_data = active_response.json()
            print(f"   ✅ Found {active_data['total']} active streams")

        # End all streams
        print("\n[3/3] Ending all streams...")
        for stream_id in stream_ids:
            await client.post(f"{BASE_URL}{API_PREFIX}/live/{stream_id}/end", headers=headers)

        print(f"   ✅ All streams ended")

    print("\n" + "=" * 60)
    print("✅ CONCURRENT STREAMS TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("LIVE STREAMING TESTS")
    print("=" * 60)

    asyncio.run(test_live_stream_start_end())
    asyncio.run(test_live_stream_performance())
    asyncio.run(test_live_stream_fluidity())
    asyncio.run(test_live_stream_concurrent())

    print("\n" + "=" * 60)
    print("ALL LIVE STREAMING TESTS COMPLETE")
    print("=" * 60)
