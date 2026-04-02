"""Test leaderboard and rewards."""

import pytest
import httpx
import asyncio
from datetime import datetime

BASE_URL = "http://localhost:8000"
API_PREFIX = "/api/v1"


async def test_leaderboard_flow():
    """Test complete leaderboard flow."""
    print("\n" + "=" * 60)
    print("TEST: LEADERBOARD FLOW")
    print("=" * 60)

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Login
        print("\n[1/4] Logging in...")
        login_response = await client.post(
            f"{BASE_URL}{API_PREFIX}/auth/login-json",
            json={"email": "anthonymillwater2@hotmail.com", "password": "GoonSite32$"},
        )

        if login_response.status_code != 200:
            print(f"   ⚠️  Login failed")
            return

        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Get my stats
        print("\n[2/4] Getting my leaderboard stats...")
        stats_response = await client.get(
            f"{BASE_URL}{API_PREFIX}/leaderboard/my-stats", headers=headers
        )

        if stats_response.status_code == 200:
            stats = stats_response.json()
            print(f"   ✅ Gems: {stats.get('gems', 0)}")
            print(f"   ✅ Monthly score: {stats.get('monthly_score', 0)}")
            print(f"   ✅ Current rank: {stats.get('current_rank', 'N/A')}")
            print(f"   ✅ Total live sessions: {stats.get('total_live_sessions', 0)}")
            print(f"   ✅ Can claim reward: {stats.get('can_claim_reward', False)}")

        # Get monthly leaderboard
        print("\n[3/4] Getting monthly leaderboard...")
        now = datetime.utcnow()
        leaderboard_response = await client.get(
            f"{BASE_URL}{API_PREFIX}/leaderboard/monthly",
            headers=headers,
            params={"year": now.year, "month": now.month, "limit": 10},
        )

        if leaderboard_response.status_code == 200:
            leaderboard = leaderboard_response.json()
            print(f"   ✅ Period: {leaderboard.get('period', 'N/A')}")
            print(f"   ✅ Entries: {len(leaderboard.get('entries', []))}")
            print(f"   ✅ My rank: {leaderboard.get('my_rank', 'N/A')}")
            print(f"   ✅ My score: {leaderboard.get('my_score', 0)}")

            # Show top 3
            entries = leaderboard.get("entries", [])[:3]
            for entry in entries:
                print(
                    f"      Rank {entry['rank']}: {entry['user_email']} - Score: {entry['total_score']}"
                )
                if entry.get("reward"):
                    print(f"         Reward: {entry['reward']}")

        # Test reward claiming (if eligible)
        print("\n[4/4] Testing reward claim...")
        if stats_response.status_code == 200:
            stats = stats_response.json()
            if stats.get("can_claim_reward"):
                claim_response = await client.post(
                    f"{BASE_URL}{API_PREFIX}/leaderboard/claim-reward", headers=headers
                )

                if claim_response.status_code == 200:
                    claim_data = claim_response.json()
                    print(f"   ✅ Reward claimed!")
                    print(f"   Rank: {claim_data.get('rank', 'N/A')}")
                    print(f"   Expires at: {claim_data.get('expires_at', 'N/A')}")
                else:
                    print(f"   ⚠️  Claim failed: {claim_response.status_code}")
            else:
                print(f"   ℹ️  Not eligible for reward (not in top 3)")

    print("\n" + "=" * 60)
    print("✅ LEADERBOARD FLOW TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_leaderboard_flow())
