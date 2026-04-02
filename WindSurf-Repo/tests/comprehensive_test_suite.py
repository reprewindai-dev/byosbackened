"""Comprehensive test suite - tests all aspects of the platform."""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
import httpx
from datetime import datetime
from typing import Dict, List, Any
import json

# Test configuration
BASE_URL = "http://localhost:8000"
API_PREFIX = "/api/v1"

# Test credentials
TEST_EMAIL = "anthonymillwater2@hotmail.com"
TEST_PASSWORD = "GoonSite32$"

# Test results
test_results = {
    "passed": [],
    "failed": [],
    "warnings": [],
    "total": 0,
}


def log_test(test_name: str, status: str, message: str = ""):
    """Log test result."""
    test_results["total"] += 1
    result = {
        "test": test_name,
        "status": status,
        "message": message,
        "timestamp": datetime.utcnow().isoformat(),
    }

    if status == "PASSED":
        test_results["passed"].append(result)
        print(f"✅ PASSED: {test_name}")
        if message:
            print(f"   {message}")
    elif status == "FAILED":
        test_results["failed"].append(result)
        print(f"❌ FAILED: {test_name}")
        print(f"   {message}")
    elif status == "WARNING":
        test_results["warnings"].append(result)
        print(f"⚠️  WARNING: {test_name}")
        print(f"   {message}")

    print()


async def test_authentication(client: httpx.AsyncClient):
    """Test authentication endpoints."""
    print("=" * 60)
    print("TESTING AUTHENTICATION")
    print("=" * 60)
    print()

    # Test login
    try:
        response = await client.post(
            f"{BASE_URL}{API_PREFIX}/auth/login-json",
            json={
                "email": TEST_EMAIL,
                "password": TEST_PASSWORD,
            },
        )

        if response.status_code == 200:
            data = response.json()
            if "access_token" in data:
                token = data["access_token"]
                log_test("Login", "PASSED", "Authentication successful")
                return token
            else:
                log_test("Login", "FAILED", "No access token in response")
                return None
        else:
            log_test("Login", "FAILED", f"Status {response.status_code}: {response.text}")
            return None
    except Exception as e:
        log_test("Login", "FAILED", f"Exception: {str(e)}")
        return None


async def test_content_endpoints(client: httpx.AsyncClient, token: str):
    """Test content endpoints."""
    print("=" * 60)
    print("TESTING CONTENT ENDPOINTS")
    print("=" * 60)
    print()

    headers = {"Authorization": f"Bearer {token}"}

    # Test list categories (public)
    try:
        response = await client.get(f"{BASE_URL}{API_PREFIX}/content/categories/list")
        if response.status_code == 200:
            categories = response.json()
            log_test("List Categories", "PASSED", f"Found {len(categories)} categories")
        else:
            log_test("List Categories", "FAILED", f"Status {response.status_code}")
    except Exception as e:
        log_test("List Categories", "FAILED", f"Exception: {str(e)}")

    # Test list content
    try:
        response = await client.get(
            f"{BASE_URL}{API_PREFIX}/content/list",
            headers=headers,
            params={"limit": 10},
        )
        if response.status_code == 200:
            content = response.json()
            log_test("List Content", "PASSED", f"Found {len(content)} items")
        else:
            log_test("List Content", "FAILED", f"Status {response.status_code}: {response.text}")
    except Exception as e:
        log_test("List Content", "FAILED", f"Exception: {str(e)}")


async def test_subscription_endpoints(client: httpx.AsyncClient, token: str):
    """Test subscription endpoints."""
    print("=" * 60)
    print("TESTING SUBSCRIPTION ENDPOINTS")
    print("=" * 60)
    print()

    headers = {"Authorization": f"Bearer {token}"}

    # Test get subscription
    try:
        response = await client.get(
            f"{BASE_URL}{API_PREFIX}/subscription/current",
            headers=headers,
        )
        if response.status_code == 200:
            subscription = response.json()
            log_test(
                "Get Subscription", "PASSED", f"Subscription status: {subscription.get('status')}"
            )
        else:
            log_test(
                "Get Subscription",
                "WARNING",
                f"Status {response.status_code} (may not have subscription)",
            )
    except Exception as e:
        log_test("Get Subscription", "FAILED", f"Exception: {str(e)}")

    # Test get pricing
    try:
        response = await client.get(f"{BASE_URL}{API_PREFIX}/subscription/pricing")
        if response.status_code == 200:
            pricing = response.json()
            log_test("Get Pricing", "PASSED", f"Found {len(pricing)} tiers")
        else:
            log_test("Get Pricing", "FAILED", f"Status {response.status_code}")
    except Exception as e:
        log_test("Get Pricing", "FAILED", f"Exception: {str(e)}")


async def test_ai_recommendations(client: httpx.AsyncClient, token: str):
    """Test AI recommendation endpoints."""
    print("=" * 60)
    print("TESTING AI RECOMMENDATIONS")
    print("=" * 60)
    print()

    headers = {"Authorization": f"Bearer {token}"}

    # Test personalized recommendations
    try:
        response = await client.get(
            f"{BASE_URL}{API_PREFIX}/ai/recommendations/personalized",
            headers=headers,
            params={"limit": 10},
        )
        if response.status_code == 200:
            data = response.json()
            recommendations = data.get("recommendations", [])
            log_test(
                "Personalized Recommendations",
                "PASSED",
                f"Got {len(recommendations)} recommendations",
            )
        else:
            log_test(
                "Personalized Recommendations",
                "FAILED",
                f"Status {response.status_code}: {response.text}",
            )
    except Exception as e:
        log_test("Personalized Recommendations", "FAILED", f"Exception: {str(e)}")

    # Test trending
    try:
        response = await client.get(
            f"{BASE_URL}{API_PREFIX}/ai/recommendations/trending",
            headers=headers,
            params={"limit": 10},
        )
        if response.status_code == 200:
            data = response.json()
            trending = data.get("trending", [])
            log_test("Trending Content", "PASSED", f"Got {len(trending)} trending items")
        else:
            log_test("Trending Content", "FAILED", f"Status {response.status_code}")
    except Exception as e:
        log_test("Trending Content", "FAILED", f"Exception: {str(e)}")

    # Test discovery feed
    try:
        response = await client.get(
            f"{BASE_URL}{API_PREFIX}/ai/recommendations/discovery-feed",
            headers=headers,
            params={"limit": 20},
        )
        if response.status_code == 200:
            data = response.json()
            feed = data.get("feed", [])
            log_test("Discovery Feed", "PASSED", f"Got {len(feed)} items in feed")
        else:
            log_test("Discovery Feed", "FAILED", f"Status {response.status_code}")
    except Exception as e:
        log_test("Discovery Feed", "FAILED", f"Exception: {str(e)}")

    # Test gooner profile
    try:
        response = await client.get(
            f"{BASE_URL}{API_PREFIX}/ai/recommendations/gooner-profile",
            headers=headers,
        )
        if response.status_code == 200:
            data = response.json()
            profile = data.get("profile", {})
            gooner_level = profile.get("gooner_level", "unknown")
            log_test("Gooner Profile", "PASSED", f"Gooner level: {gooner_level}")
        else:
            log_test("Gooner Profile", "FAILED", f"Status {response.status_code}")
    except Exception as e:
        log_test("Gooner Profile", "FAILED", f"Exception: {str(e)}")

    # Test desires
    try:
        response = await client.get(
            f"{BASE_URL}{API_PREFIX}/ai/recommendations/desires",
            headers=headers,
        )
        if response.status_code == 200:
            data = response.json()
            desires = data.get("desires", {})
            log_test("Desire Prediction", "PASSED", "Desires predicted successfully")
        else:
            log_test("Desire Prediction", "FAILED", f"Status {response.status_code}")
    except Exception as e:
        log_test("Desire Prediction", "FAILED", f"Exception: {str(e)}")


async def test_security_endpoints(client: httpx.AsyncClient, token: str):
    """Test security endpoints."""
    print("=" * 60)
    print("TESTING SECURITY ENDPOINTS")
    print("=" * 60)
    print()

    headers = {"Authorization": f"Bearer {token}"}

    # Test security status
    try:
        response = await client.get(
            f"{BASE_URL}{API_PREFIX}/security/status",
            headers=headers,
        )
        if response.status_code == 200:
            data = response.json()
            status = data.get("status", "unknown")
            log_test("Security Status", "PASSED", f"Security status: {status}")
        else:
            log_test("Security Status", "FAILED", f"Status {response.status_code}")
    except Exception as e:
        log_test("Security Status", "FAILED", f"Exception: {str(e)}")

    # Test vulnerability scan
    try:
        response = await client.get(
            f"{BASE_URL}{API_PREFIX}/security/scan",
            headers=headers,
        )
        if response.status_code == 200:
            data = response.json()
            score = data.get("overall_score", 0)
            log_test("Vulnerability Scan", "PASSED", f"Security score: {score}")
        else:
            log_test("Vulnerability Scan", "FAILED", f"Status {response.status_code}")
    except Exception as e:
        log_test("Vulnerability Scan", "FAILED", f"Exception: {str(e)}")


async def test_admin_endpoints(client: httpx.AsyncClient, token: str):
    """Test admin endpoints."""
    print("=" * 60)
    print("TESTING ADMIN ENDPOINTS")
    print("=" * 60)
    print()

    headers = {"Authorization": f"Bearer {token}"}

    # Test admin stats
    try:
        response = await client.get(
            f"{BASE_URL}{API_PREFIX}/admin/stats",
            headers=headers,
        )
        if response.status_code == 200:
            data = response.json()
            log_test("Admin Stats", "PASSED", "Admin stats retrieved")
        elif response.status_code == 403:
            log_test("Admin Stats", "WARNING", "Admin access required (may not be admin)")
        else:
            log_test("Admin Stats", "FAILED", f"Status {response.status_code}")
    except Exception as e:
        log_test("Admin Stats", "FAILED", f"Exception: {str(e)}")

    # Test payment stats
    try:
        response = await client.get(
            f"{BASE_URL}{API_PREFIX}/admin/payments/stats",
            headers=headers,
        )
        if response.status_code == 200:
            data = response.json()
            log_test("Payment Stats", "PASSED", "Payment stats retrieved")
        elif response.status_code == 403:
            log_test("Payment Stats", "WARNING", "Admin access required")
        else:
            log_test("Payment Stats", "FAILED", f"Status {response.status_code}")
    except Exception as e:
        log_test("Payment Stats", "FAILED", f"Exception: {str(e)}")


async def test_conversion_flow(client: httpx.AsyncClient, token: str):
    """Test conversion flow (subscription creation)."""
    print("=" * 60)
    print("TESTING CONVERSION FLOW")
    print("=" * 60)
    print()

    headers = {"Authorization": f"Bearer {token}"}

    # Test get pricing
    try:
        response = await client.get(f"{BASE_URL}{API_PREFIX}/subscription/pricing")
        if response.status_code == 200:
            pricing = response.json()
            if pricing:
                tier = pricing[0]  # Get first tier
                tier_name = tier.get("tier", "premium")

                # Test create subscription (would create payment)
                try:
                    response = await client.post(
                        f"{BASE_URL}{API_PREFIX}/subscription/create",
                        headers=headers,
                        json={
                            "tier": tier_name,
                            "payment_provider": "bitcoin",
                        },
                    )
                    if response.status_code in [200, 201]:
                        data = response.json()
                        if "payment_url" in data or "subscription" in data:
                            log_test(
                                "Create Subscription", "PASSED", "Subscription creation initiated"
                            )
                        else:
                            log_test(
                                "Create Subscription",
                                "WARNING",
                                "Subscription created but no payment URL",
                            )
                    else:
                        log_test(
                            "Create Subscription",
                            "WARNING",
                            f"Status {response.status_code}: {response.text}",
                        )
                except Exception as e:
                    log_test("Create Subscription", "WARNING", f"Exception: {str(e)}")

                log_test("Get Pricing", "PASSED", f"Found {len(pricing)} tiers")
            else:
                log_test("Get Pricing", "WARNING", "No pricing tiers found")
        else:
            log_test("Get Pricing", "FAILED", f"Status {response.status_code}")
    except Exception as e:
        log_test("Get Pricing", "FAILED", f"Exception: {str(e)}")


async def test_error_handling(client: httpx.AsyncClient, token: str):
    """Test error handling."""
    print("=" * 60)
    print("TESTING ERROR HANDLING")
    print("=" * 60)
    print()

    headers = {"Authorization": f"Bearer {token}"}

    # Test invalid endpoint
    try:
        response = await client.get(
            f"{BASE_URL}{API_PREFIX}/invalid/endpoint",
            headers=headers,
        )
        if response.status_code == 404:
            log_test("404 Error Handling", "PASSED", "404 handled correctly")
        else:
            log_test("404 Error Handling", "WARNING", f"Unexpected status: {response.status_code}")
    except Exception as e:
        log_test("404 Error Handling", "FAILED", f"Exception: {str(e)}")

    # Test invalid token
    try:
        response = await client.get(
            f"{BASE_URL}{API_PREFIX}/content/list",
            headers={"Authorization": "Bearer invalid_token"},
        )
        if response.status_code == 401:
            log_test("401 Error Handling", "PASSED", "401 handled correctly")
        else:
            log_test("401 Error Handling", "WARNING", f"Unexpected status: {response.status_code}")
    except Exception as e:
        log_test("401 Error Handling", "FAILED", f"Exception: {str(e)}")

    # Test invalid input
    try:
        response = await client.post(
            f"{BASE_URL}{API_PREFIX}/security/validate-input",
            headers=headers,
            json={"input_text": "<script>alert('xss')</script>"},
        )
        if response.status_code == 200:
            data = response.json()
            if not data.get("is_valid", True):
                log_test("Input Validation", "PASSED", "XSS attempt blocked")
            else:
                log_test("Input Validation", "WARNING", "XSS not blocked")
        else:
            log_test("Input Validation", "WARNING", f"Status {response.status_code}")
    except Exception as e:
        log_test("Input Validation", "FAILED", f"Exception: {str(e)}")


async def test_performance(client: httpx.AsyncClient, token: str):
    """Test performance and response times."""
    print("=" * 60)
    print("TESTING PERFORMANCE")
    print("=" * 60)
    print()

    headers = {"Authorization": f"Bearer {token}"}

    # Test response times
    endpoints_to_test = [
        ("List Categories", f"{BASE_URL}{API_PREFIX}/content/categories/list", None),
        ("List Content", f"{BASE_URL}{API_PREFIX}/content/list", headers),
        (
            "Personalized Recommendations",
            f"{BASE_URL}{API_PREFIX}/ai/recommendations/personalized",
            headers,
        ),
        ("Get Pricing", f"{BASE_URL}{API_PREFIX}/subscription/pricing", None),
    ]

    for name, url, test_headers in endpoints_to_test:
        try:
            import time

            start = time.time()
            response = await client.get(url, headers=test_headers, timeout=10.0)
            elapsed = time.time() - start

            if response.status_code == 200:
                if elapsed < 2.0:
                    log_test(f"{name} Performance", "PASSED", f"Response time: {elapsed:.2f}s")
                elif elapsed < 5.0:
                    log_test(f"{name} Performance", "WARNING", f"Slow response: {elapsed:.2f}s")
                else:
                    log_test(f"{name} Performance", "FAILED", f"Very slow: {elapsed:.2f}s")
            else:
                log_test(f"{name} Performance", "WARNING", f"Status {response.status_code}")
        except Exception as e:
            log_test(f"{name} Performance", "FAILED", f"Exception: {str(e)}")


async def run_all_tests():
    """Run all tests."""
    print("=" * 60)
    print("COMPREHENSIVE PLATFORM TEST SUITE")
    print("=" * 60)
    print()
    print(f"Testing platform at: {BASE_URL}")
    print(f"Test user: {TEST_EMAIL}")
    print()

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Test authentication first
        token = await test_authentication(client)

        if not token:
            print("❌ Authentication failed. Cannot continue tests.")
            return

        # Run all test suites
        await test_content_endpoints(client, token)
        await test_subscription_endpoints(client, token)
        await test_ai_recommendations(client, token)
        await test_security_endpoints(client, token)
        await test_admin_endpoints(client, token)
        await test_conversion_flow(client, token)
        await test_error_handling(client, token)
        await test_performance(client, token)

    # Print summary
    print()
    print("=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print()
    print(f"Total Tests: {test_results['total']}")
    print(f"✅ Passed: {len(test_results['passed'])}")
    print(f"❌ Failed: {len(test_results['failed'])}")
    print(f"⚠️  Warnings: {len(test_results['warnings'])}")
    print()

    if test_results["failed"]:
        print("FAILED TESTS:")
        for test in test_results["failed"]:
            print(f"  - {test['test']}: {test['message']}")
        print()

    if test_results["warnings"]:
        print("WARNINGS:")
        for test in test_results["warnings"]:
            print(f"  - {test['test']}: {test['message']}")
        print()

    # Calculate success rate
    success_rate = (
        (len(test_results["passed"]) / test_results["total"] * 100)
        if test_results["total"] > 0
        else 0
    )
    print(f"Success Rate: {success_rate:.1f}%")
    print()

    if success_rate >= 90:
        print("✅ PLATFORM STATUS: EXCELLENT")
    elif success_rate >= 75:
        print("⚠️  PLATFORM STATUS: GOOD (some issues)")
    elif success_rate >= 50:
        print("⚠️  PLATFORM STATUS: NEEDS ATTENTION")
    else:
        print("❌ PLATFORM STATUS: CRITICAL ISSUES")

    # Save results
    results_file = Path(__file__).parent.parent / "test_results.json"
    with open(results_file, "w") as f:
        json.dump(test_results, f, indent=2)

    print(f"\nResults saved to: {results_file}")


if __name__ == "__main__":
    asyncio.run(run_all_tests())
