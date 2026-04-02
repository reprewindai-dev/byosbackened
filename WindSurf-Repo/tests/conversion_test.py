"""Test conversion flow end-to-end."""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
import httpx
from datetime import datetime

BASE_URL = "http://localhost:8000"
API_PREFIX = "/api/v1"
TEST_EMAIL = "anthonymillwater2@hotmail.com"
TEST_PASSWORD = "GoonSite32$"


async def test_conversion_flow():
    """Test complete conversion flow."""
    print("=" * 60)
    print("CONVERSION FLOW TEST")
    print("=" * 60)
    print()

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Step 1: Login
        print("Step 1: User Login")
        try:
            response = await client.post(
                f"{BASE_URL}{API_PREFIX}/auth/login-json",
                json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
            )
            if response.status_code != 200:
                print(f"❌ Login failed: {response.status_code}")
                return
            token = response.json()["access_token"]
            print("✅ Login successful")
        except Exception as e:
            print(f"❌ Login error: {e}")
            return

        headers = {"Authorization": f"Bearer {token}"}

        # Step 2: Browse content (public)
        print("\nStep 2: Browse Content")
        try:
            response = await client.get(f"{BASE_URL}{API_PREFIX}/content/categories/list")
            if response.status_code == 200:
                categories = response.json()
                print(f"✅ Found {len(categories)} categories")
            else:
                print(f"⚠️  Categories: {response.status_code}")
        except Exception as e:
            print(f"⚠️  Categories error: {e}")

        # Step 3: View content (requires subscription)
        print("\nStep 3: View Content")
        try:
            response = await client.get(
                f"{BASE_URL}{API_PREFIX}/content/list",
                headers=headers,
                params={"limit": 5},
            )
            if response.status_code == 200:
                content = response.json()
                print(f"✅ Found {len(content)} content items")
            elif response.status_code == 403:
                print("⚠️  Subscription required (expected)")
            else:
                print(f"⚠️  Content access: {response.status_code}")
        except Exception as e:
            print(f"⚠️  Content error: {e}")

        # Step 4: Get pricing
        print("\nStep 4: View Pricing")
        try:
            response = await client.get(f"{BASE_URL}{API_PREFIX}/subscription/pricing")
            if response.status_code == 200:
                pricing = response.json()
                print(f"✅ Found {len(pricing)} subscription tiers")
                for tier in pricing:
                    print(f"   - {tier.get('tier')}: ${tier.get('price', 0)}/month")
            else:
                print(f"❌ Pricing failed: {response.status_code}")
        except Exception as e:
            print(f"❌ Pricing error: {e}")

        # Step 5: Create subscription (conversion)
        print("\nStep 5: Create Subscription (Conversion)")
        try:
            response = await client.post(
                f"{BASE_URL}{API_PREFIX}/subscription/create",
                headers=headers,
                json={
                    "tier": "premium",
                    "payment_provider": "bitcoin",
                },
            )
            if response.status_code in [200, 201]:
                data = response.json()
                if "payment_url" in data:
                    print(f"✅ Subscription created, payment URL: {data['payment_url'][:50]}...")
                elif "subscription" in data:
                    print("✅ Subscription created")
                else:
                    print("⚠️  Subscription created but no payment URL")
            else:
                print(f"⚠️  Subscription creation: {response.status_code}")
                print(f"   Response: {response.text[:200]}")
        except Exception as e:
            print(f"⚠️  Subscription error: {e}")

        # Step 6: Test AI recommendations
        print("\nStep 6: AI Recommendations")
        try:
            response = await client.get(
                f"{BASE_URL}{API_PREFIX}/ai/recommendations/personalized",
                headers=headers,
                params={"limit": 5},
            )
            if response.status_code == 200:
                data = response.json()
                recommendations = data.get("recommendations", [])
                print(f"✅ Got {len(recommendations)} personalized recommendations")
            else:
                print(f"⚠️  Recommendations: {response.status_code}")
        except Exception as e:
            print(f"⚠️  Recommendations error: {e}")

        print("\n" + "=" * 60)
        print("CONVERSION FLOW TEST COMPLETE")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_conversion_flow())
