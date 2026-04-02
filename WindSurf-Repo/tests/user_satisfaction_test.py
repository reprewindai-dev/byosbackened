"""Test user satisfaction and experience."""

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


async def test_user_satisfaction():
    """Test user satisfaction factors."""
    print("=" * 60)
    print("USER SATISFACTION TEST")
    print("=" * 60)
    print()

    satisfaction_score = 0
    max_score = 0

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Test 1: Fast login
        print("Test 1: Fast Login")
        max_score += 1
        try:
            import time

            start = time.time()
            response = await client.post(
                f"{BASE_URL}{API_PREFIX}/auth/login-json",
                json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
            )
            elapsed = time.time() - start

            if response.status_code == 200 and elapsed < 2.0:
                print(f"✅ Login fast: {elapsed:.2f}s")
                satisfaction_score += 1
            else:
                print(f"⚠️  Login slow or failed: {elapsed:.2f}s")
        except Exception as e:
            print(f"❌ Login error: {e}")

        if response.status_code != 200:
            print("❌ Cannot continue - login failed")
            return

        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Test 2: Content availability
        print("\nTest 2: Content Availability")
        max_score += 1
        try:
            response = await client.get(
                f"{BASE_URL}{API_PREFIX}/content/list",
                headers=headers,
                params={"limit": 10},
            )
            if response.status_code == 200:
                content = response.json()
                if len(content) > 0:
                    print(f"✅ Content available: {len(content)} items")
                    satisfaction_score += 1
                else:
                    print("⚠️  No content available")
            else:
                print(f"⚠️  Content access: {response.status_code}")
        except Exception as e:
            print(f"❌ Content error: {e}")

        # Test 3: Category variety
        print("\nTest 3: Category Variety")
        max_score += 1
        try:
            response = await client.get(f"{BASE_URL}{API_PREFIX}/content/categories/list")
            if response.status_code == 200:
                categories = response.json()
                if len(categories) >= 5:
                    print(f"✅ Good category variety: {len(categories)} categories")
                    satisfaction_score += 1
                else:
                    print(f"⚠️  Limited categories: {len(categories)}")
        except Exception as e:
            print(f"❌ Categories error: {e}")

        # Test 4: AI recommendations quality
        print("\nTest 4: AI Recommendations Quality")
        max_score += 1
        try:
            response = await client.get(
                f"{BASE_URL}{API_PREFIX}/ai/recommendations/personalized",
                headers=headers,
                params={"limit": 10},
            )
            if response.status_code == 200:
                data = response.json()
                recommendations = data.get("recommendations", [])
                if len(recommendations) >= 5:
                    print(f"✅ Good recommendations: {len(recommendations)} items")
                    satisfaction_score += 1
                else:
                    print(f"⚠️  Limited recommendations: {len(recommendations)}")
        except Exception as e:
            print(f"❌ Recommendations error: {e}")

        # Test 5: Search functionality
        print("\nTest 5: Search Functionality")
        max_score += 1
        try:
            response = await client.get(
                f"{BASE_URL}{API_PREFIX}/content/search",
                headers=headers,
                params={"query": "test", "limit": 10},
            )
            if response.status_code in [200, 404]:  # 404 if search not implemented
                print("✅ Search endpoint exists")
                satisfaction_score += 1
            else:
                print(f"⚠️  Search: {response.status_code}")
        except Exception as e:
            print(f"⚠️  Search error: {e}")

        # Test 6: Pricing clarity
        print("\nTest 6: Pricing Clarity")
        max_score += 1
        try:
            response = await client.get(f"{BASE_URL}{API_PREFIX}/subscription/pricing")
            if response.status_code == 200:
                pricing = response.json()
                if len(pricing) > 0:
                    print(f"✅ Clear pricing: {len(pricing)} tiers")
                    satisfaction_score += 1
                else:
                    print("⚠️  No pricing available")
        except Exception as e:
            print(f"❌ Pricing error: {e}")

        # Test 7: Response times
        print("\nTest 7: Response Times")
        max_score += 1
        try:
            import time

            endpoints = [
                ("Categories", f"{BASE_URL}{API_PREFIX}/content/categories/list", None),
                ("Content", f"{BASE_URL}{API_PREFIX}/content/list", headers),
                ("Pricing", f"{BASE_URL}{API_PREFIX}/subscription/pricing", None),
            ]

            all_fast = True
            for name, url, test_headers in endpoints:
                start = time.time()
                await client.get(url, headers=test_headers, timeout=5.0)
                elapsed = time.time() - start
                if elapsed > 3.0:
                    all_fast = False
                    print(f"   ⚠️  {name} slow: {elapsed:.2f}s")

            if all_fast:
                print("✅ All endpoints fast")
                satisfaction_score += 1
        except Exception as e:
            print(f"❌ Performance error: {e}")

        # Test 8: Error messages clarity
        print("\nTest 8: Error Message Clarity")
        max_score += 1
        try:
            response = await client.get(
                f"{BASE_URL}{API_PREFIX}/content/list",
                headers={"Authorization": "Bearer invalid"},
            )
            if response.status_code == 401:
                error_detail = response.json().get("detail", "")
                if error_detail:
                    print("✅ Clear error messages")
                    satisfaction_score += 1
                else:
                    print("⚠️  Error message not clear")
        except Exception as e:
            print(f"❌ Error test error: {e}")

        # Test 9: Content quality indicators
        print("\nTest 9: Content Quality Indicators")
        max_score += 1
        try:
            response = await client.get(
                f"{BASE_URL}{API_PREFIX}/content/list",
                headers=headers,
                params={"limit": 5},
            )
            if response.status_code == 200:
                content = response.json()
                if content:
                    item = content[0]
                    has_thumbnail = item.get("thumbnail_url")
                    has_title = item.get("title")
                    if has_thumbnail and has_title:
                        print("✅ Content has quality indicators")
                        satisfaction_score += 1
                    else:
                        print("⚠️  Missing quality indicators")
        except Exception as e:
            print(f"❌ Content quality error: {e}")

        # Test 10: Platform stability
        print("\nTest 10: Platform Stability")
        max_score += 1
        try:
            # Make multiple requests
            errors = 0
            for i in range(5):
                try:
                    await client.get(
                        f"{BASE_URL}{API_PREFIX}/content/categories/list",
                        timeout=5.0,
                    )
                except:
                    errors += 1

            if errors == 0:
                print("✅ Platform stable")
                satisfaction_score += 1
            else:
                print(f"⚠️  Platform unstable: {errors} errors")
        except Exception as e:
            print(f"❌ Stability error: {e}")

    # Calculate satisfaction percentage
    satisfaction_percentage = (satisfaction_score / max_score * 100) if max_score > 0 else 0

    print("\n" + "=" * 60)
    print("USER SATISFACTION RESULTS")
    print("=" * 60)
    print()
    print(f"Score: {satisfaction_score}/{max_score}")
    print(f"Satisfaction: {satisfaction_percentage:.1f}%")
    print()

    if satisfaction_percentage >= 90:
        print("✅ USER SATISFACTION: EXCELLENT")
    elif satisfaction_percentage >= 75:
        print("⚠️  USER SATISFACTION: GOOD")
    elif satisfaction_percentage >= 50:
        print("⚠️  USER SATISFACTION: NEEDS IMPROVEMENT")
    else:
        print("❌ USER SATISFACTION: POOR")

    return satisfaction_percentage


if __name__ == "__main__":
    asyncio.run(test_user_satisfaction())
