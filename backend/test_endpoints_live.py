"""Quick live endpoint test — run against localhost:8765."""
import httpx
import json
import time

BASE = "http://localhost:8765"

def test_public():
    print("=== PUBLIC ENDPOINTS ===")
    tests = [
        ("GET", "/"),
        ("GET", "/health"),
        ("GET", "/status"),
        ("GET", "/api/v1/subscriptions/plans"),
    ]
    with httpx.Client(timeout=10, follow_redirects=False) as c:
        for method, path in tests:
            r = c.get(f"{BASE}{path}")
            ct = r.headers.get("content-type", "")[:30]
            if "html" in ct:
                summary = f"[HTML {len(r.text)} chars]"
            else:
                try:
                    summary = json.dumps(r.json())[:100]
                except:
                    summary = r.text[:100]
            status = "PASS" if r.status_code < 400 else "FAIL"
            print(f"  [{status}] {r.status_code} {method} {path}  ->  {summary}")


def test_auth_flow():
    print("\n=== AUTH FLOW ===")
    with httpx.Client(timeout=10) as c:
        email = f"ep_test_{int(time.time())}@test.com"
        # Register
        r = c.post(f"{BASE}/api/v1/auth/register", json={
            "email": email, "password": "TestPass123!", "name": "T", "workspace_name": "TW"
        })
        print(f"  Register: {r.status_code} -> {r.text[:120]}")

        # Login
        r = c.post(f"{BASE}/api/v1/auth/login", json={
            "email": email, "password": "TestPass123!"
        })
        print(f"  Login: {r.status_code} -> {r.text[:150]}")

        if r.status_code != 200:
            print("  Cannot get token, skipping auth tests")
            return

        data = r.json()
        token = data.get("access_token") or data.get("token")
        if not token:
            print(f"  No token in response: {list(data.keys())}")
            return

        headers = {"Authorization": f"Bearer {token}"}
        print(f"  Token: {token[:30]}...")

        # Test authenticated endpoints
        print("\n=== AUTHENTICATED ENDPOINTS ===")
        auth_tests = [
            # Auth
            "/api/v1/auth/me",
            "/api/v1/auth/api-keys",
            # Wallet
            "/api/v1/wallet/balance",
            "/api/v1/wallet/transactions",
            "/api/v1/wallet/topup/options",
            "/api/v1/wallet/stats/usage",
            # Billing
            "/api/v1/billing/breakdown",
            "/api/v1/billing/report",
            # Budget
            "/api/v1/budget",
            "/api/v1/budget/forecast",
            # Cost
            "/api/v1/cost/history",
            "/api/v1/cost/kill-switch/status",
            # Routing
            "/api/v1/routing/policy",
            # Plugins
            "/api/v1/plugins",
            # Compliance
            "/api/v1/compliance/regulations",
            # Insights
            "/api/v1/insights/summary",
            "/api/v1/insights/savings",
            # Suggestions
            "/api/v1/suggestions",
            "/api/v1/suggestions/summary",
            # Audit
            "/api/v1/audit/logs",
            # Monitoring
            "/api/v1/monitoring/health",
            "/api/v1/monitoring/dashboard",
            "/api/v1/monitoring/metrics",
            "/api/v1/monitoring/metrics/history",
            # Security
            "/api/v1/security/events",
            "/api/v1/security/stats",
            "/api/v1/security/dashboard",
            "/api/v1/security/alerts",
            # Content Safety
            "/api/v1/content-safety/logs",
            "/api/v1/content-safety/age-verification/status",
            # Locker Security
            "/api/v1/locker/security/events",
            "/api/v1/locker/security/dashboard",
            "/api/v1/locker/security/controls",
            "/api/v1/locker/security/threats/stats",
            # Locker Monitoring
            "/api/v1/locker/monitoring/status",
            "/api/v1/locker/monitoring/alerts",
            "/api/v1/locker/monitoring/alerts/summary",
            "/api/v1/locker/monitoring/health/detailed",
            "/api/v1/locker/monitoring/metrics/performance",
            # Locker Users
            "/api/v1/locker/users/",
            # Subscriptions
            "/api/v1/subscriptions/current",
            "/api/v1/subscriptions/plans",
            # Admin
            "/api/v1/admin/overview",
            # Autonomous
            "/api/v1/autonomous/routing/stats",
            # Metrics (top-level)
            "/metrics",
        ]

        ok_count = 0
        fail_count = 0
        for path in auth_tests:
            try:
                r = c.get(f"{BASE}{path}", headers=headers)
                if r.status_code < 400:
                    ok_count += 1
                    print(f"  PASS {r.status_code} GET {path}")
                else:
                    fail_count += 1
                    try:
                        summary = json.dumps(r.json())[:80]
                    except:
                        summary = r.text[:80]
                    print(f"  FAIL {r.status_code} GET {path}  ->  {summary}")
            except Exception as e:
                fail_count += 1
                print(f"  ERR GET {path}  ->  {e}")

        print(f"\n  Result: {ok_count} OK, {fail_count} FAIL")


if __name__ == "__main__":
    test_public()
    test_auth_flow()
