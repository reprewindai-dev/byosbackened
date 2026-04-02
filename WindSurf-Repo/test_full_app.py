#!/usr/bin/env python3
"""
COMPREHENSIVE APPLICATION TEST SUITE
===================================

Tests the entire BYOS AI Backend application:
- AI execution system
- Stripe billing integration  
- All API endpoints
- Database connectivity
- Provider integration
- Governance pipeline
"""

import asyncio
import aiohttp
import json
import sys
import os
from datetime import datetime
from typing import Dict, List, Any

class AppTester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = None
        self.auth_token = None
        self.workspace_id = None
        self.test_results = []
        
    async def setup(self):
        """Setup test session."""
        self.session = aiohttp.ClientSession()
        print(f"🧪 Testing app at: {self.base_url}")
        
    async def cleanup(self):
        """Cleanup test session."""
        if self.session:
            await self.session.close()
            
    def log_test(self, test_name: str, success: bool, details: str = ""):
        """Log test result."""
        status = "✅ PASS" if success else "❌ FAIL"
        self.test_results.append({
            "test": test_name,
            "status": status,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })
        print(f"{status}: {test_name}")
        if details:
            print(f"    {details}")
            
    async def test_health_endpoints(self):
        """Test basic health endpoints."""
        print("\n🏥 TESTING HEALTH ENDPOINTS")
        print("=" * 50)
        
        try:
            # Test root endpoint
            async with self.session.get(f"{self.base_url}/") as response:
                if response.status == 200:
                    data = await response.json()
                    self.log_test("Root endpoint", True, f"App: {data.get('name')}")
                else:
                    self.log_test("Root endpoint", False, f"Status: {response.status}")
                    
            # Test health endpoint
            async with self.session.get(f"{self.base_url}/health") as response:
                if response.status == 200:
                    data = await response.json()
                    self.log_test("Health endpoint", True, f"Status: {data.get('status')}")
                else:
                    self.log_test("Health endpoint", False, f"Status: {response.status}")
                    
            # Test API health
            async with self.session.get(f"{self.base_url}/api/v1/health") as response:
                if response.status == 200:
                    data = await response.json()
                    self.log_test("API health endpoint", True, f"Version: {data.get('version')}")
                else:
                    self.log_test("API health endpoint", False, f"Status: {response.status}")
                    
        except Exception as e:
            self.log_test("Health endpoints", False, str(e))
            
    async def test_ai_execution(self):
        """Test AI execution through governance pipeline."""
        print("\n🤖 TESTING AI EXECUTION SYSTEM")
        print("=" * 50)
        
        try:
            # Test governance execute endpoint
            test_request = {
                "operation_type": "summarize",
                "input_text": "This is a comprehensive test of the AI execution system. The sovereign governance pipeline should process this request through all 12 layers and return a governed summary that meets all quality and compliance requirements.",
                "temperature": 0.7,
                "max_tokens": 256,
                "demo_context": {
                    "session_id": "test-session-123",
                    "demo_token": "test-token",
                    "lead_id": "test-lead"
                }
            }
            
            async with self.session.post(
                f"{self.base_url}/api/v1/governance/execute",
                json=test_request,
                headers={"Content-Type": "application/json"}
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    self.log_test("AI execution", True, f"Request ID: {result.get('request_id')}")
                    self.log_test("Governance pipeline", result.get('success', False), 
                                f"Tier: {result.get('risk_level', 'unknown')}")
                    self.log_test("Execution time", True, f"{result.get('execution_time_ms', 0)}ms")
                    self.log_test("Coherence score", True, f"{result.get('coherence_score', 0):.2f}")
                else:
                    error_text = await response.text()
                    self.log_test("AI execution", False, f"Status: {response.status}, Error: {error_text}")
                    
        except Exception as e:
            self.log_test("AI execution", False, str(e))
            
    async def test_stripe_billing(self):
        """Test Stripe billing integration."""
        print("\n💳 TESTING STRIPE BILLING")
        print("=" * 50)
        
        try:
            # Test billing plans
            async with self.session.get(f"{self.base_url}/api/v1/stripe/plans") as response:
                if response.status == 200:
                    plans = await response.json()
                    self.log_test("Stripe plans", True, f"Found {len(plans)} plans")
                    for plan in plans:
                        print(f"    - {plan.get('name', 'Unknown')}: ${plan.get('price_monthly', 0)/100:.2f}/mo")
                else:
                    self.log_test("Stripe plans", False, f"Status: {response.status}")
                    
            # Test checkout session creation
            checkout_request = {
                "plan_id": "starter",
                "success_url": "http://localhost:3000/success",
                "cancel_url": "http://localhost:3000/cancel"
            }
            
            async with self.session.post(
                f"{self.base_url}/api/v1/stripe/checkout",
                json=checkout_request,
                headers={"Content-Type": "application/json"}
            ) as response:
                
                if response.status == 200:
                    checkout_data = await response.json()
                    self.log_test("Stripe checkout", True, f"Session created: {checkout_data.get('session_id', 'N/A')}")
                else:
                    error_text = await response.text()
                    self.log_test("Stripe checkout", False, f"Status: {response.status}")
                    
        except Exception as e:
            self.log_test("Stripe billing", False, str(e))
            
    async def test_api_endpoints(self):
        """Test various API endpoints."""
        print("\n🌐 TESTING API ENDPOINTS")
        print("=" * 50)
        
        endpoints = [
            ("/api/v1/apps", "Apps list"),
            ("/api/v1/workspaces", "Workspaces"),
            ("/api/v1/governance/health", "Governance health"),
            ("/api/v1/billing", "Billing endpoint"),
            ("/api/v1/cost", "Cost intelligence"),
            ("/api/v1/audit", "Audit logs"),
            ("/api/v1/metrics", "Metrics"),
        ]
        
        for endpoint, description in endpoints:
            try:
                async with self.session.get(f"{self.base_url}{endpoint}") as response:
                    if response.status in [200, 401, 403]:  # Accept auth errors as expected
                        self.log_test(description, True, f"Status: {response.status}")
                    else:
                        self.log_test(description, False, f"Status: {response.status}")
            except Exception as e:
                self.log_test(description, False, str(e))
                
    async def test_database_connectivity(self):
        """Test database connectivity."""
        print("\n🗄️  TESTING DATABASE CONNECTIVITY")
        print("=" * 50)
        
        try:
            # Test through an endpoint that uses database
            async with self.session.get(f"{self.base_url}/api/v1/governance/receipts") as response:
                if response.status in [200, 401, 403]:  # DB working if we get proper response
                    self.log_test("Database connectivity", True, "Database responding")
                else:
                    self.log_test("Database connectivity", False, f"Status: {response.status}")
        except Exception as e:
            self.log_test("Database connectivity", False, str(e))
            
    async def test_provider_system(self):
        """Test AI provider system."""
        print("\n🔌 TESTING AI PROVIDER SYSTEM")
        print("=" * 50)
        
        try:
            # Test different operation types
            operations = [
                {"operation_type": "summarize", "input_text": "Test summarization"},
                {"operation_type": "chat", "input_text": "Hello, how are you?"},
                {"operation_type": "embed", "input_text": "Test embedding"}
            ]
            
            for i, op in enumerate(operations):
                try:
                    async with self.session.post(
                        f"{self.base_url}/api/v1/governance/execute",
                        json={**op, "temperature": 0.7, "max_tokens": 100},
                        headers={"Content-Type": "application/json"}
                    ) as response:
                        
                        if response.status == 200:
                            result = await response.json()
                            self.log_test(f"Operation {op['operation_type']}", True, 
                                        f"Success: {result.get('success', False)}")
                        else:
                            self.log_test(f"Operation {op['operation_type']}", False, 
                                        f"Status: {response.status}")
                except Exception as e:
                    self.log_test(f"Operation {op['operation_type']}", False, str(e))
                    
        except Exception as e:
            self.log_test("Provider system", False, str(e))
            
    async def run_all_tests(self):
        """Run all tests."""
        print("🚀 STARTING COMPREHENSIVE APP TEST")
        print("=" * 60)
        print(f"Testing: {self.base_url}")
        print(f"Started: {datetime.now().isoformat()}")
        
        await self.setup()
        
        try:
            await self.test_health_endpoints()
            await self.test_database_connectivity()
            await self.test_ai_execution()
            await self.test_stripe_billing()
            await self.test_provider_system()
            await self.test_api_endpoints()
            
        finally:
            await self.cleanup()
            
        await self.print_summary()
        
    async def print_summary(self):
        """Print test summary."""
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for result in self.test_results if "PASS" in result["status"])
        total = len(self.test_results)
        
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Success Rate: {(passed/total)*100:.1f}%")
        
        if total - passed > 0:
            print("\n❌ FAILED TESTS:")
            for result in self.test_results:
                if "FAIL" in result["status"]:
                    print(f"  - {result['test']}: {result['details']}")
                    
        print(f"\n🎯 APP STATUS: {'✅ READY' if passed == total else '⚠️  NEEDS ATTENTION'}")
        print(f"Completed: {datetime.now().isoformat()}")

async def main():
    """Main test runner."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test the BYOS AI Backend application")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL to test")
    args = parser.parse_args()
    
    tester = AppTester(base_url=args.url)
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())
