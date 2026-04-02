"""Complete platform test - all features."""

import pytest
import httpx
import asyncio
import time
from datetime import datetime

BASE_URL = "http://localhost:8000"
API_PREFIX = "/api/v1"


async def test_complete_platform():
    """Test complete platform functionality."""
    print("\n" + "=" * 80)
    print("COMPLETE PLATFORM TEST - ALL FEATURES")
    print("=" * 80)

    results = {
        "user_uploads": False,
        "admin_approval": False,
        "live_streaming": False,
        "gamification": False,
        "leaderboard": False,
        "rewards": False,
        "performance": False,
        "fluidity": False,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Login as admin
        print("\n[PHASE 1] Authentication...")
        login_response = await client.post(
            f"{BASE_URL}{API_PREFIX}/auth/login-json",
            json={"email": "anthonymillwater2@hotmail.com", "password": "GoonSite32$"},
        )

        if login_response.status_code != 200:
            print(f"   ❌ Login failed: {login_response.status_code}")
            return results

        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print(f"   ✅ Admin logged in")

        # Test 1: User Uploads
        print("\n[PHASE 2] Testing User Uploads...")
        try:
            test_content = b"test video content"
            files = {"file": ("test.mp4", test_content, "video/mp4")}
            data = {"title": "Test Upload", "tags": "test"}

            upload_response = await client.post(
                f"{BASE_URL}{API_PREFIX}/user-uploads/upload",
                headers=headers,
                files=files,
                data=data,
            )

            if upload_response.status_code == 201:
                upload_data = upload_response.json()
                content_id = upload_data["id"]
                print(f"   ✅ Upload successful: {content_id}")
                results["user_uploads"] = True
            else:
                print(f"   ⚠️  Upload status: {upload_response.status_code}")
        except Exception as e:
            print(f"   ❌ Upload error: {e}")

        # Test 2: Admin Approval
        print("\n[PHASE 3] Testing Admin Approval...")
        try:
            pending_response = await client.get(
                f"{BASE_URL}{API_PREFIX}/admin/approval/pending", headers=headers
            )

            if pending_response.status_code == 200:
                pending_data = pending_response.json()
                print(f"   ✅ Found {pending_data['total']} pending items")
                results["admin_approval"] = True

                # Approve if content exists
                if pending_data["total"] > 0 and "content_id" in locals():
                    approve_response = await client.post(
                        f"{BASE_URL}{API_PREFIX}/admin/approval/approve",
                        headers=headers,
                        json={"content_id": content_id, "approve": True, "notes": "Test approval"},
                    )
                    if approve_response.status_code == 200:
                        print(f"   ✅ Content approved")
            else:
                print(f"   ⚠️  Pending check failed: {pending_response.status_code}")
        except Exception as e:
            print(f"   ❌ Approval error: {e}")

        # Test 3: Live Streaming
        print("\n[PHASE 4] Testing Live Streaming...")
        try:
            # Start stream
            start_response = await client.post(
                f"{BASE_URL}{API_PREFIX}/live/start",
                headers=headers,
                json={
                    "title": "Complete Platform Test Stream",
                    "chat_enabled": True,
                    "gifts_enabled": True,
                },
            )

            if start_response.status_code == 201:
                stream_data = start_response.json()
                stream_id = stream_data["stream_id"]
                print(f"   ✅ Stream started: {stream_id}")
                results["live_streaming"] = True

                # Join as viewer
                join_response = await client.post(
                    f"{BASE_URL}{API_PREFIX}/live/{stream_id}/join", headers=headers
                )
                if join_response.status_code == 200:
                    print(f"   ✅ Joined stream")

                # Send gift
                gift_response = await client.post(
                    f"{BASE_URL}{API_PREFIX}/live/{stream_id}/gift",
                    headers=headers,
                    params={"gift_type": "rose"},
                )
                if gift_response.status_code == 200:
                    print(f"   ✅ Gift sent")
                    results["gamification"] = True

                # Wait a bit
                await asyncio.sleep(2)

                # End stream
                end_response = await client.post(
                    f"{BASE_URL}{API_PREFIX}/live/{stream_id}/end", headers=headers
                )
                if end_response.status_code == 200:
                    end_data = end_response.json()
                    print(f"   ✅ Stream ended - Gems earned: {end_data.get('gems_earned', 0)}")
            else:
                print(f"   ⚠️  Stream start failed: {start_response.status_code}")
        except Exception as e:
            print(f"   ❌ Live streaming error: {e}")

        # Test 4: Performance
        print("\n[PHASE 5] Testing Performance (No Buffering)...")
        try:
            # Start stream
            start_response = await client.post(
                f"{BASE_URL}{API_PREFIX}/live/start",
                headers=headers,
                json={"title": "Performance Test"},
            )

            if start_response.status_code == 201:
                stream_id = start_response.json()["stream_id"]

                # Rapid operations
                operation_times = []
                for i in range(20):
                    op_start = time.time()
                    await client.post(
                        f"{BASE_URL}{API_PREFIX}/live/{stream_id}/join", headers=headers
                    )
                    op_duration = time.time() - op_start
                    operation_times.append(op_duration)
                    await asyncio.sleep(0.05)

                avg_time = sum(operation_times) / len(operation_times)
                max_time = max(operation_times)

                print(f"   ✅ Average operation time: {avg_time:.3f}s")
                print(f"   ✅ Max operation time: {max_time:.3f}s")

                if avg_time < 0.5 and max_time < 1.0:
                    print(f"   ✅ No buffering detected - fluid operation")
                    results["performance"] = True
                    results["fluidity"] = True
                else:
                    print(f"   ⚠️  Some operations slow")

                # End stream
                await client.post(f"{BASE_URL}{API_PREFIX}/live/{stream_id}/end", headers=headers)
        except Exception as e:
            print(f"   ❌ Performance test error: {e}")

        # Test 5: Leaderboard
        print("\n[PHASE 6] Testing Leaderboard...")
        try:
            leaderboard_response = await client.get(
                f"{BASE_URL}{API_PREFIX}/leaderboard/monthly", headers=headers
            )

            if leaderboard_response.status_code == 200:
                leaderboard = leaderboard_response.json()
                print(f"   ✅ Leaderboard loaded")
                print(f"   Entries: {len(leaderboard.get('entries', []))}")
                print(f"   My rank: {leaderboard.get('my_rank', 'N/A')}")
                results["leaderboard"] = True

                # Check stats
                stats_response = await client.get(
                    f"{BASE_URL}{API_PREFIX}/leaderboard/my-stats", headers=headers
                )
                if stats_response.status_code == 200:
                    stats = stats_response.status_code.json()
                    print(f"   ✅ Stats loaded")
                    if stats.get("can_claim_reward"):
                        results["rewards"] = True
            else:
                print(f"   ⚠️  Leaderboard failed: {leaderboard_response.status_code}")
        except Exception as e:
            print(f"   ❌ Leaderboard error: {e}")

    # Summary
    print("\n" + "=" * 80)
    print("TEST RESULTS SUMMARY")
    print("=" * 80)

    for feature, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"   {status} - {feature}")

    total_passed = sum(1 for p in results.values() if p)
    total_tests = len(results)

    print(f"\n   Total: {total_passed}/{total_tests} tests passed")

    if total_passed == total_tests:
        print("\n   🎉 ALL TESTS PASSED - PLATFORM FULLY FUNCTIONAL")
    else:
        print(f"\n   ⚠️  {total_tests - total_passed} tests failed")

    print("=" * 80)

    return results


if __name__ == "__main__":
    asyncio.run(test_complete_platform())
