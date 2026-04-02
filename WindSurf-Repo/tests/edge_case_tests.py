"""Test edge cases and error scenarios."""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
import httpx

BASE_URL = "http://localhost:8000"
API_PREFIX = "/api/v1"
TEST_EMAIL = "anthonymillwater2@hotmail.com"
TEST_PASSWORD = "GoonSite32$"


async def test_edge_cases():
    """Test edge cases."""
    print("=" * 60)
    print("EDGE CASE TESTS")
    print("=" * 60)
    print()

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Login first
        try:
            response = await client.post(
                f"{BASE_URL}{API_PREFIX}/auth/login-json",
                json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
            )
            token = response.json().get("access_token") if response.status_code == 200 else None
        except:
            token = None

        headers = {"Authorization": f"Bearer {token}"} if token else {}

        # Test 1: Very long input
        print("Test 1: Very Long Input")
        try:
            long_input = "a" * 10000
            response = await client.post(
                f"{BASE_URL}{API_PREFIX}/security/validate-input",
                headers=headers,
                json={"input_text": long_input, "max_length": 1000},
            )
            if response.status_code == 200:
                data = response.json()
                if not data.get("is_valid"):
                    print("✅ Long input rejected correctly")
                else:
                    print("⚠️  Long input not rejected")
            else:
                print(f"⚠️  Status: {response.status_code}")
        except Exception as e:
            print(f"⚠️  Error: {e}")

        # Test 2: SQL injection attempt
        print("\nTest 2: SQL Injection Attempt")
        try:
            sql_injection = "'; DROP TABLE users; --"
            response = await client.post(
                f"{BASE_URL}{API_PREFIX}/security/validate-input",
                headers=headers,
                json={"input_text": sql_injection},
            )
            if response.status_code == 200:
                data = response.json()
                if not data.get("is_valid"):
                    print("✅ SQL injection blocked")
                else:
                    print("❌ SQL injection not blocked")
            else:
                print(f"⚠️  Status: {response.status_code}")
        except Exception as e:
            print(f"⚠️  Error: {e}")

        # Test 3: XSS attempt
        print("\nTest 3: XSS Attempt")
        try:
            xss = "<script>alert('xss')</script>"
            response = await client.post(
                f"{BASE_URL}{API_PREFIX}/security/validate-input",
                headers=headers,
                json={"input_text": xss},
            )
            if response.status_code == 200:
                data = response.json()
                if not data.get("is_valid"):
                    print("✅ XSS blocked")
                else:
                    print("❌ XSS not blocked")
            else:
                print(f"⚠️  Status: {response.status_code}")
        except Exception as e:
            print(f"⚠️  Error: {e}")

        # Test 4: Invalid token
        print("\nTest 4: Invalid Token")
        try:
            response = await client.get(
                f"{BASE_URL}{API_PREFIX}/content/list",
                headers={"Authorization": "Bearer invalid_token_12345"},
            )
            if response.status_code == 401:
                print("✅ Invalid token rejected")
            else:
                print(f"⚠️  Unexpected status: {response.status_code}")
        except Exception as e:
            print(f"⚠️  Error: {e}")

        # Test 5: Missing token
        print("\nTest 5: Missing Token")
        try:
            response = await client.get(f"{BASE_URL}{API_PREFIX}/content/list")
            if response.status_code == 401:
                print("✅ Missing token rejected")
            else:
                print(f"⚠️  Unexpected status: {response.status_code}")
        except Exception as e:
            print(f"⚠️  Error: {e}")

        # Test 6: Rate limiting (if implemented)
        print("\nTest 6: Rate Limiting")
        try:
            # Make many rapid requests
            for i in range(10):
                await client.get(f"{BASE_URL}{API_PREFIX}/content/categories/list")

            # Check if rate limited
            response = await client.get(f"{BASE_URL}{API_PREFIX}/content/categories/list")
            if response.status_code == 429:
                print("✅ Rate limiting active")
            else:
                print("⚠️  Rate limiting not triggered (may be normal)")
        except Exception as e:
            print(f"⚠️  Error: {e}")

        # Test 7: Invalid endpoint
        print("\nTest 7: Invalid Endpoint")
        try:
            response = await client.get(
                f"{BASE_URL}{API_PREFIX}/invalid/endpoint/123",
                headers=headers,
            )
            if response.status_code == 404:
                print("✅ 404 handled correctly")
            else:
                print(f"⚠️  Unexpected status: {response.status_code}")
        except Exception as e:
            print(f"⚠️  Error: {e}")

        # Test 8: Empty/null values
        print("\nTest 8: Empty/Null Values")
        try:
            response = await client.post(
                f"{BASE_URL}{API_PREFIX}/auth/login-json",
                json={"email": "", "password": ""},
            )
            if response.status_code != 200:
                print("✅ Empty credentials rejected")
            else:
                print("⚠️  Empty credentials accepted")
        except Exception as e:
            print(f"⚠️  Error: {e}")

        print("\n" + "=" * 60)
        print("EDGE CASE TESTS COMPLETE")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_edge_cases())
