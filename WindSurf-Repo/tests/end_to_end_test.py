"""End-to-end test of complete user journey."""

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


async def test_complete_user_journey():
    """Test complete user journey from start to finish."""
    print("=" * 60)
    print("END-TO-END USER JOURNEY TEST")
    print("=" * 60)
    print()

    journey_steps = []

    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        # STEP 1: User visits site (public access)
        print("STEP 1: User Visits Site")
        try:
            response = await client.get(f"{BASE_URL}/static/premium.html")
            if response.status_code == 200:
                print("✅ Frontend loads successfully")
                journey_steps.append({"step": "Frontend Load", "status": "PASSED"})
            else:
                print(f"❌ Frontend failed: {response.status_code}")
                journey_steps.append({"step": "Frontend Load", "status": "FAILED"})
        except Exception as e:
            print(f"❌ Frontend error: {e}")
            journey_steps.append({"step": "Frontend Load", "status": "FAILED"})

        # STEP 2: User views public categories
        print("\nSTEP 2: User Views Categories (Public)")
        try:
            response = await client.get(f"{BASE_URL}{API_PREFIX}/content/categories/list")
            if response.status_code == 200:
                categories = response.json()
                print(f"✅ Categories visible: {len(categories)} categories")
                journey_steps.append(
                    {"step": "View Categories", "status": "PASSED", "data": len(categories)}
                )
            else:
                print(f"❌ Categories failed: {response.status_code}")
                journey_steps.append({"step": "View Categories", "status": "FAILED"})
        except Exception as e:
            print(f"❌ Categories error: {e}")
            journey_steps.append({"step": "View Categories", "status": "FAILED"})

        # STEP 3: User views pricing
        print("\nSTEP 3: User Views Pricing")
        try:
            response = await client.get(f"{BASE_URL}{API_PREFIX}/subscription/pricing")
            if response.status_code == 200:
                pricing = response.json()
                print(f"✅ Pricing visible: {len(pricing)} tiers")
                for tier in pricing:
                    print(f"   - {tier.get('tier')}: ${tier.get('price', 0)}/month")
                journey_steps.append(
                    {"step": "View Pricing", "status": "PASSED", "data": len(pricing)}
                )
            else:
                print(f"❌ Pricing failed: {response.status_code}")
                journey_steps.append({"step": "View Pricing", "status": "FAILED"})
        except Exception as e:
            print(f"❌ Pricing error: {e}")
            journey_steps.append({"step": "View Pricing", "status": "FAILED"})

        # STEP 4: User registers/logs in
        print("\nSTEP 4: User Login")
        try:
            response = await client.post(
                f"{BASE_URL}{API_PREFIX}/auth/login-json",
                json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
            )
            if response.status_code == 200:
                data = response.json()
                token = data.get("access_token")
                if token:
                    print("✅ Login successful")
                    journey_steps.append({"step": "Login", "status": "PASSED"})
                else:
                    print("❌ No token received")
                    journey_steps.append({"step": "Login", "status": "FAILED"})
                    return
            else:
                print(f"❌ Login failed: {response.status_code}")
                journey_steps.append({"step": "Login", "status": "FAILED"})
                return
        except Exception as e:
            print(f"❌ Login error: {e}")
            journey_steps.append({"step": "Login", "status": "FAILED"})
            return

        headers = {"Authorization": f"Bearer {token}"}

        # STEP 5: User tries to access content (may need subscription)
        print("\nSTEP 5: User Accesses Content")
        try:
            response = await client.get(
                f"{BASE_URL}{API_PREFIX}/content/list",
                headers=headers,
                params={"limit": 5},
            )
            if response.status_code == 200:
                content = response.json()
                print(f"✅ Content accessible: {len(content)} items")
                journey_steps.append(
                    {"step": "Access Content", "status": "PASSED", "data": len(content)}
                )
            elif response.status_code == 403:
                print("⚠️  Subscription required (expected for conversion)")
                journey_steps.append({"step": "Access Content", "status": "SUBSCRIPTION_REQUIRED"})
            else:
                print(f"⚠️  Content access: {response.status_code}")
                journey_steps.append({"step": "Access Content", "status": "WARNING"})
        except Exception as e:
            print(f"❌ Content error: {e}")
            journey_steps.append({"step": "Access Content", "status": "FAILED"})

        # STEP 6: User gets AI recommendations
        print("\nSTEP 6: User Gets AI Recommendations")
        try:
            response = await client.get(
                f"{BASE_URL}{API_PREFIX}/ai/recommendations/personalized",
                headers=headers,
                params={"limit": 5},
            )
            if response.status_code == 200:
                data = response.json()
                recommendations = data.get("recommendations", [])
                print(f"✅ Recommendations available: {len(recommendations)} items")
                journey_steps.append(
                    {"step": "AI Recommendations", "status": "PASSED", "data": len(recommendations)}
                )
            else:
                print(f"⚠️  Recommendations: {response.status_code}")
                journey_steps.append({"step": "AI Recommendations", "status": "WARNING"})
        except Exception as e:
            print(f"❌ Recommendations error: {e}")
            journey_steps.append({"step": "AI Recommendations", "status": "FAILED"})

        # STEP 7: User creates subscription (CONVERSION)
        print("\nSTEP 7: User Creates Subscription (CONVERSION)")
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
                    payment_url = data["payment_url"]
                    print(f"✅ Subscription created, payment URL generated")
                    print(f"   Payment URL: {payment_url[:60]}...")
                    journey_steps.append(
                        {"step": "Create Subscription", "status": "PASSED", "conversion": True}
                    )
                elif "subscription" in data:
                    print("✅ Subscription created")
                    journey_steps.append(
                        {"step": "Create Subscription", "status": "PASSED", "conversion": True}
                    )
                else:
                    print("⚠️  Subscription created but no payment URL")
                    journey_steps.append({"step": "Create Subscription", "status": "WARNING"})
            else:
                print(f"⚠️  Subscription creation: {response.status_code}")
                print(f"   Response: {response.text[:200]}")
                journey_steps.append({"step": "Create Subscription", "status": "WARNING"})
        except Exception as e:
            print(f"⚠️  Subscription error: {e}")
            journey_steps.append({"step": "Create Subscription", "status": "WARNING"})

        # STEP 8: User accesses content after subscription
        print("\nSTEP 8: User Accesses Content After Subscription")
        try:
            response = await client.get(
                f"{BASE_URL}{API_PREFIX}/content/list",
                headers=headers,
                params={"limit": 10},
            )
            if response.status_code == 200:
                content = response.json()
                print(f"✅ Content accessible after subscription: {len(content)} items")
                journey_steps.append({"step": "Post-Subscription Access", "status": "PASSED"})
            elif response.status_code == 403:
                print("⚠️  Still requires subscription (payment may be pending)")
                journey_steps.append(
                    {"step": "Post-Subscription Access", "status": "PENDING_PAYMENT"}
                )
            else:
                print(f"⚠️  Access: {response.status_code}")
                journey_steps.append({"step": "Post-Subscription Access", "status": "WARNING"})
        except Exception as e:
            print(f"❌ Post-subscription error: {e}")
            journey_steps.append({"step": "Post-Subscription Access", "status": "FAILED"})

        # STEP 9: User gets optimized recommendations
        print("\nSTEP 9: User Gets Optimized Recommendations")
        try:
            response = await client.get(
                f"{BASE_URL}{API_PREFIX}/ai/recommendations/gooner-content",
                headers=headers,
                params={"limit": 10},
            )
            if response.status_code == 200:
                data = response.json()
                content = data.get("content", [])
                print(f"✅ Optimized recommendations: {len(content)} items")
                journey_steps.append({"step": "Optimized Recommendations", "status": "PASSED"})
            else:
                print(f"⚠️  Optimized recommendations: {response.status_code}")
                journey_steps.append({"step": "Optimized Recommendations", "status": "WARNING"})
        except Exception as e:
            print(f"❌ Optimized recommendations error: {e}")
            journey_steps.append({"step": "Optimized Recommendations", "status": "WARNING"})

        # STEP 10: User gets continuous flow
        print("\nSTEP 10: User Gets Continuous Content Flow")
        try:
            response = await client.get(
                f"{BASE_URL}{API_PREFIX}/ai/recommendations/continuous-flow",
                headers=headers,
                params={"limit": 20},
            )
            if response.status_code == 200:
                data = response.json()
                flow = data.get("flow", [])
                print(f"✅ Continuous flow: {len(flow)} items")
                journey_steps.append({"step": "Continuous Flow", "status": "PASSED"})
            else:
                print(f"⚠️  Continuous flow: {response.status_code}")
                journey_steps.append({"step": "Continuous Flow", "status": "WARNING"})
        except Exception as e:
            print(f"❌ Continuous flow error: {e}")
            journey_steps.append({"step": "Continuous Flow", "status": "WARNING"})

    # Summary
    print("\n" + "=" * 60)
    print("JOURNEY SUMMARY")
    print("=" * 60)
    print()

    passed = sum(1 for s in journey_steps if s["status"] == "PASSED")
    failed = sum(1 for s in journey_steps if s["status"] == "FAILED")
    warnings = sum(
        1
        for s in journey_steps
        if s["status"] in ["WARNING", "SUBSCRIPTION_REQUIRED", "PENDING_PAYMENT"]
    )

    print(f"Total Steps: {len(journey_steps)}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"⚠️  Warnings: {warnings}")
    print()

    conversion_success = any(s.get("conversion") for s in journey_steps)
    if conversion_success:
        print("✅ CONVERSION FLOW: SUCCESS")
    else:
        print("⚠️  CONVERSION FLOW: NEEDS ATTENTION")

    print()
    print("Journey Steps:")
    for i, step in enumerate(journey_steps, 1):
        status_icon = (
            "✅" if step["status"] == "PASSED" else "❌" if step["status"] == "FAILED" else "⚠️"
        )
        print(f"  {i}. {status_icon} {step['step']}: {step['status']}")
        if "data" in step:
            print(f"     Data: {step['data']}")

    return journey_steps


if __name__ == "__main__":
    asyncio.run(test_complete_user_journey())
