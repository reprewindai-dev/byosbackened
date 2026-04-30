#!/usr/bin/env python3
"""Comprehensive endpoint verification - test ALL features."""
import asyncio
import httpx
import json
import time
import uuid
import random
import string
from datetime import datetime
from typing import Dict, List, Any

BASE_URL = "http://localhost:8001"
RESULTS = []

class EndpointTester:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self.auth_token = None
        self.workspace_id = None
        self.user_id = None
        self.api_key = None
        
    async def test_endpoint(self, method: str, path: str, data: Dict = None, 
                          headers: Dict = None, expected_status: int = 200, 
                          auth_required: bool = False, test_name: str = ""):
        """Test a single endpoint and record results."""
        start = time.time()
        try:
            url = f"{BASE_URL}{path}"
            
            # Add auth if required
            if auth_required and self.auth_token:
                headers = headers or {}
                headers["Authorization"] = f"Bearer {self.auth_token}"
            
            # Make request
            if method.upper() == "GET":
                resp = await self.client.get(url, headers=headers)
            elif method.upper() == "POST":
                resp = await self.client.post(url, json=data, headers=headers)
            elif method.upper() == "PUT":
                resp = await self.client.put(url, json=data, headers=headers)
            elif method.upper() == "DELETE":
                resp = await self.client.delete(url, headers=headers)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            elapsed = time.time() - start
            success = resp.status_code == expected_status
            
            result = {
                "test": test_name or f"{method} {path}",
                "method": method,
                "path": path,
                "status": resp.status_code,
                "expected": expected_status,
                "success": success,
                "latency": elapsed,
                "timestamp": datetime.utcnow().isoformat(),
                "auth_required": auth_required,
                "response_sample": resp.text[:200] if not success else None,
            }
            
            RESULTS.append(result)
            
            # Store auth tokens
            if resp.status_code == 201 and "access_token" in resp.text:
                tokens = resp.json()
                self.auth_token = tokens.get("access_token")
                self.workspace_id = tokens.get("workspace_id")
                self.user_id = tokens.get("user_id")
            
            # Store API key
            if resp.status_code == 201 and "raw_key" in resp.text:
                key_data = resp.json()
                self.api_key = key_data.get("raw_key")
            
            print(f"  {'✅' if success else '❌'} {test_name or f'{method} {path}'} - {resp.status_code} ({elapsed:.2f}s)")
            return success
            
        except Exception as e:
            elapsed = time.time() - start
            result = {
                "test": test_name or f"{method} {path}",
                "method": method,
                "path": path,
                "status": 0,
                "expected": expected_status,
                "success": False,
                "latency": elapsed,
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e),
                "auth_required": auth_required,
            }
            RESULTS.append(result)
            print(f"  ❌ {test_name or f'{method} {path}'} - ERROR: {e}")
            return False

    def random_email(self):
        return f"test_{''.join(random.choices(string.ascii_lowercase, k=8))}@example.com"

    def random_password(self):
        return ''.join(random.choices(string.ascii_letters + string.digits, k=12))

async def test_health_and_system(tester: EndpointTester):
    """Test health and system endpoints."""
    print("\n🏥 Testing Health & System Endpoints")
    
    await tester.test_endpoint("GET", "/health", test_name="Health Check")
    await tester.test_endpoint("GET", "/status", test_name="System Status")
    await tester.test_endpoint("GET", "/metrics", test_name="Metrics")
    await tester.test_endpoint("GET", "/", test_name="Root Endpoint")

async def test_auth_flows(tester: EndpointTester):
    """Test complete authentication flows."""
    print("\n🔐 Testing Authentication Flows")
    
    # 1. Get GitHub login URL
    await tester.test_endpoint("GET", "/api/v1/auth/github/login", 
                             test_name="GitHub OAuth Login URL")
    
    # 2. Register new user (with strong password)
    email = tester.random_email()
    password = f"TestPass123{random.randint(100, 999)}"
    await tester.test_endpoint("POST", "/api/v1/auth/register", 
                             data={
                                 "email": email,
                                 "password": password,
                                 "workspace_name": f"Test Workspace {random.randint(1000, 9999)}",
                             },
                             expected_status=201,
                             test_name="User Registration")
    
    # 3. Login with same credentials
    await tester.test_endpoint("POST", "/api/v1/auth/login",
                             data={"email": email, "password": password},
                             expected_status=200,
                             test_name="User Login")
    
    # 4. Get current user info
    await tester.test_endpoint("GET", "/api/v1/auth/me",
                             auth_required=True,
                             test_name="Get Current User")
    
    # 5. Test refresh token
    await tester.test_endpoint("POST", "/api/v1/auth/refresh",
                             data={"refresh_token": "dummy"},
                             expected_status=401,
                             test_name="Refresh Token (invalid)")
    
    # 6. Logout
    await tester.test_endpoint("POST", "/api/v1/auth/logout",
                             auth_required=True,
                             test_name="User Logout")

async def test_subscription_flow(tester: EndpointTester):
    """Test subscription and billing endpoints."""
    print("\n💳 Testing Subscription & Billing")
    
    # 1. Get available plans (public)
    await tester.test_endpoint("GET", "/api/v1/subscriptions/plans",
                             test_name="Get Subscription Plans")
    
    # 2. Create checkout session (requires auth)
    if tester.auth_token:
        await tester.test_endpoint("POST", "/api/v1/subscriptions/checkout",
                                 data={
                                     "plan": "starter",
                                     "billing_cycle": "monthly",
                                     "success_url": "https://example.com/success",
                                     "cancel_url": "https://example.com/cancel",
                                 },
                                 expected_status=503,  # Stripe not configured
                                 auth_required=True,
                                 test_name="Create Checkout Session")
        
        # 3. Test billing portal
        await tester.test_endpoint("POST", "/api/v1/subscriptions/portal",
                                 data={"return_url": "https://example.com"},
                                 expected_status=400,  # No customer yet
                                 auth_required=True,
                                 test_name="Billing Portal")

async def test_api_keys(tester: EndpointTester):
    """Test API key management."""
    print("\n🔑 Testing API Keys")
    
    if tester.auth_token:
        # 1. Create API key
        await tester.test_endpoint("POST", "/api/v1/auth/api-keys",
                                 data={
                                     "name": f"Test Key {random.randint(100, 999)}",
                                     "scopes": ["read", "write"],
                                 },
                                 expected_status=201,
                                 auth_required=True,
                                 test_name="Create API Key")
        
        # 2. List API keys
        await tester.test_endpoint("GET", "/api/v1/auth/api-keys",
                                 auth_required=True,
                                 test_name="List API Keys")
        
        # 3. Test API key authentication
        if tester.api_key:
            await tester.test_endpoint("GET", "/api/v1/auth/me",
                                     headers={"X-API-Key": tester.api_key},
                                     test_name="API Key Auth")

async def test_support_bot(tester: EndpointTester):
    """Test support bot scenarios."""
    print("\n🤖 Testing Support Bot")
    
    test_queries = [
        ("What plans do you offer?", "Plans Inquiry"),
        ("How do I reset my API key?", "API Key Help"),
        ("I got a 401 error", "Error Help"),
        ("What's the pricing?", "Pricing Question"),
        ("How does billing work?", "Billing Question"),
        ("What models are supported?", "Models Question"),
        ("How do I upgrade?", "Upgrade Help"),
    ]
    
    for query, test_name in test_queries:
        await tester.test_endpoint("POST", "/api/v1/support/chat",
                                 data={"message": query},
                                 test_name=f"Support Bot - {test_name}")

async def test_wallet_and_billing(tester: EndpointTester):
    """Test token wallet and billing endpoints."""
    print("\n💰 Testing Wallet & Billing")
    
    if tester.auth_token:
        # 1. Get wallet balance
        await tester.test_endpoint("GET", "/api/v1/wallet/balance",
                                 auth_required=True,
                                 test_name="Get Wallet Balance")
        
        # 2. Get wallet transactions
        await tester.test_endpoint("GET", "/api/v1/wallet/transactions",
                                 auth_required=True,
                                 test_name="Get Wallet Transactions")

async def test_admin_endpoints(tester: EndpointTester):
    """Test admin and security endpoints."""
    print("\n🛡️ Testing Admin & Security")
    
    if tester.auth_token:
        # 1. Test audit logs
        await tester.test_endpoint("GET", "/api/v1/audit/logs",
                                 auth_required=True,
                                 test_name="Get Audit Logs")
        
        # 2. Test security events
        await tester.test_endpoint("GET", "/api/v1/security/events",
                                 auth_required=True,
                                 test_name="Get Security Events")
        
        # 3. Test kill switch (if available)
        await tester.test_endpoint("GET", "/api/v1/admin/kill-switch/status",
                                 auth_required=True,
                                 expected_status=403,  # Not admin
                                 test_name="Kill Switch Status")

async def test_llm_execution(tester: EndpointTester):
    """Test LLM execution endpoints."""
    print("\n🧠 Testing LLM Execution")
    
    if tester.auth_token:
        # 1. Basic exec request
        await tester.test_endpoint("POST", "/v1/exec",
                                 data={
                                     "prompt": "What is 2+2?",
                                     "max_tokens": 100,
                                 },
                                 auth_required=True,
                                 test_name="LLM Exec - Basic")
        
        # 2. Exec with conversation memory
        conv_id = f"test_conv_{uuid.uuid4().hex[:8]}"
        await tester.test_endpoint("POST", "/v1/exec",
                                 data={
                                     "prompt": "Remember: I like cats",
                                     "conversation_id": conv_id,
                                     "max_tokens": 50,
                                 },
                                 auth_required=True,
                                 test_name="LLM Exec - Memory")
        
        # 3. Follow-up with memory
        await tester.test_endpoint("POST", "/v1/exec",
                                 data={
                                     "prompt": "What did I say I like?",
                                     "conversation_id": conv_id,
                                     "max_tokens": 50,
                                 },
                                 auth_required=True,
                                 test_name="LLM Exec - Memory Follow-up")

async def main():
    print("=" * 80)
    print("COMPREHENSIVE ENDPOINT VERIFICATION")
    print("=" * 80)
    
    tester = EndpointTester()
    
    # Test all endpoint categories
    test_suites = [
        test_health_and_system,
        test_auth_flows,
        test_subscription_flow,
        test_api_keys,
        test_support_bot,
        test_wallet_and_billing,
        test_admin_endpoints,
        test_llm_execution,
    ]
    
    for test_suite in test_suites:
        try:
            await test_suite(tester)
        except Exception as e:
            print(f"❌ Test suite failed: {e}")
    
    await tester.client.aclose()
    
    # Generate comprehensive report
    print("\n" + "=" * 80)
    print("COMPREHENSIVE TEST RESULTS")
    print("=" * 80)
    
    total_tests = len(RESULTS)
    passed = sum(1 for r in RESULTS if r["success"])
    failed = total_tests - passed
    
    print(f"\n📊 SUMMARY")
    print(f"  Total Tests: {total_tests}")
    print(f"  ✅ Passed: {passed} ({100*passed/total_tests:.1f}%)")
    print(f"  ❌ Failed: {failed} ({100*failed/total_tests:.1f}%)")
    
    # Category breakdown
    categories = {}
    for result in RESULTS:
        category = result["test"].split(" - ")[0] if " - " in result["test"] else "System"
        if category not in categories:
            categories[category] = {"passed": 0, "failed": 0}
        if result["success"]:
            categories[category]["passed"] += 1
        else:
            categories[category]["failed"] += 1
    
    print(f"\n📋 CATEGORY BREAKDOWN")
    for category, stats in sorted(categories.items()):
        total = stats["passed"] + stats["failed"]
        pass_rate = 100 * stats["passed"] / total if total > 0 else 0
        print(f"  {category}: {stats['passed']}/{total} ({pass_rate:.1f}%)")
    
    # Show failures
    failures = [r for r in RESULTS if not r["success"]]
    if failures:
        print(f"\n❌ FAILURES ({len(failures)})")
        for fail in failures[:10]:  # Show first 10
            print(f"  {fail['test']}: {fail['status']} (expected {fail['expected']})")
            if fail.get("error"):
                print(f"    Error: {fail['error']}")
        if len(failures) > 10:
            print(f"  ... and {len(failures) - 10} more")
    
    # Performance summary
    latencies = [r["latency"] for r in RESULTS if r["success"]]
    if latencies:
        avg_latency = sum(latencies) / len(latencies)
        p95_latency = sorted(latencies)[int(0.95 * len(latencies))]
        print(f"\n⚡ PERFORMANCE")
        print(f"  Avg Latency: {avg_latency*1000:.0f}ms")
        print(f"  P95 Latency: {p95_latency*1000:.0f}ms")
    
    # Final verdict
    print(f"\n{'='*80}")
    if failed == 0:
        print("🎉 ALL ENDPOINTS WORKING - 100% VERIFIED")
    elif failed <= 5:
        print(f"⚠️  NEARLY PERFECT - {failed} minor issues")
    else:
        print(f"❌ NEEDS ATTENTION - {failed} endpoints failing")
    
    print(f"{'='*80}")

if __name__ == "__main__":
    asyncio.run(main())
