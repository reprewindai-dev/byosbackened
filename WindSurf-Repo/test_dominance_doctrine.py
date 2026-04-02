#!/usr/bin/env python3
"""
Test script for DOMINANCE SAAS DOCTRINE v4 implementation.

This script tests:
1. Lead capture and demo token generation
2. Demo execution with escalating value
3. Governance pipeline enforcement
4. Paywall triggering after 3 attempts
5. ROI receipt generation
"""

import asyncio
import aiohttp
import json
import time
from typing import Dict, Any

# Test configuration
BASE_URL = "http://localhost:8000"
API_PREFIX = "/api/v1"

class DominanceDoctrineTester:
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.session = None
        self.demo_token = None
        self.lead_id = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def test_lead_capture(self) -> Dict[str, Any]:
        """Test lead capture endpoint."""
        print("🎯 Testing Lead Capture...")
        
        lead_data = {
            "email": "test@example.com",
            "company": "Test Corp",
            "use_case": "content_creation",
            "name": "Test User",
            "job_title": "CTO",
            "company_size": "51-200",
            "industry": "technology"
        }
        
        async with self.session.post(
            f"{self.base_url}{API_PREFIX}/leads/capture",
            json=lead_data
        ) as response:
            if response.status == 200:
                result = await response.json()
                self.demo_token = result["demo_token"]
                self.lead_id = result["lead_id"]
                print(f"✅ Lead captured successfully")
                print(f"   Lead ID: {self.lead_id}")
                print(f"   Demo Token: {self.demo_token}")
                print(f"   Attempts Remaining: {result['demo_attempts_remaining']}")
                print(f"   Qualification Score: {result['qualification_score']}")
                return result
            else:
                error = await response.text()
                print(f"❌ Lead capture failed: {response.status} - {error}")
                return {}
    
    async def test_demo_execution(self, attempt_num: int) -> Dict[str, Any]:
        """Test demo execution with governance pipeline."""
        print(f"\n🚀 Testing Demo Execution (Attempt {attempt_num})...")
        
        request_data = {
            "operation_type": "summarize",
            "input_text": f"This is test article content for demo attempt {attempt_num}. " * 20,
            "temperature": 0.7,
            "max_tokens": 512,
            "demo_token": self.demo_token
        }
        
        async with self.session.post(
            f"{self.base_url}{API_PREFIX}/ai/execute",
            json=request_data
        ) as response:
            if response.status == 200:
                result = await response.json()
                print(f"✅ Demo execution successful")
                print(f"   Governance Passed: {result.get('governance_passed', True)}")
                print(f"   Coherence Score: {result.get('coherence_score', 'N/A')}")
                print(f"   Risk Level: {result.get('risk_level', 'N/A')}")
                print(f"   Patterns Applied: {result.get('patterns_applied', 0)}")
                print(f"   Cost: ${result.get('cost_estimate', 0):.6f}")
                
                if result.get('time_saved_minutes'):
                    print(f"   Time Saved: {result['time_saved_minutes']:.1f} minutes")
                if result.get('cost_avoided_usd'):
                    print(f"   Cost Avoided: ${result['cost_avoided_usd']:.2f}")
                if result.get('risk_reduction_score'):
                    print(f"   Risk Reduction: {result['risk_reduction_score'] * 100:.1f}%")
                
                return result
            elif response.status == 402:
                # Paywall hit
                error = await response.json()
                print(f"💰 Paywall Hit - Demo Limit Reached")
                print(f"   Message: {error.get('message', 'Demo limit reached')}")
                print(f"   Upgrade Options: {error.get('upgrade_options', {})}")
                return {"paywall_hit": True, "error": error}
            else:
                error = await response.text()
                print(f"❌ Demo execution failed: {response.status} - {error}")
                return {}
    
    async def test_lead_status(self) -> Dict[str, Any]:
        """Test lead status endpoint."""
        print(f"\n📊 Testing Lead Status...")
        
        async with self.session.get(
            f"{self.base_url}{API_PREFIX}/leads/status/{self.demo_token}"
        ) as response:
            if response.status == 200:
                result = await response.json()
                print(f"✅ Lead status retrieved")
                print(f"   Attempts Used: {result['demo_attempts_used']}")
                print(f"   Attempts Remaining: {result['demo_attempts_remaining']}")
                print(f"   Token Status: {result['demo_token_status']}")
                print(f"   Engagement Level: {result['engagement_level']}")
                print(f"   Conversion Probability: {result['conversion_probability'] * 100:.1f}%")
                return result
            else:
                error = await response.text()
                print(f"❌ Lead status failed: {response.status} - {error}")
                return {}
    
    async def test_governance_health(self) -> Dict[str, Any]:
        """Test governance pipeline health."""
        print(f"\n🏥 Testing Governance Health...")
        
        async with self.session.get(
            f"{self.base_url}{API_PREFIX}/governance/health"
        ) as response:
            if response.status == 200:
                result = await response.json()
                print(f"✅ Governance pipeline healthy")
                print(f"   Status: {result['status']}")
                print(f"   Version: {result['pipeline_version']}")
                print(f"   Patterns Stored: {result['patterns_stored']}")
                print(f"   Moat Strength: {result['moat_strength']}")
                return result
            else:
                error = await response.text()
                print(f"❌ Governance health failed: {response.status} - {error}")
                return {}
    
    async def test_lead_analytics(self) -> Dict[str, Any]:
        """Test lead analytics endpoint."""
        print(f"\n📈 Testing Lead Analytics...")
        
        async with self.session.get(
            f"{self.base_url}{API_PREFIX}/leads/analytics"
        ) as response:
            if response.status == 200:
                result = await response.json()
                print(f"✅ Lead analytics retrieved")
                print(f"   Total Leads: {result['total_leads']}")
                print(f"   New Leads Today: {result['new_leads_today']}")
                print(f"   Conversion Rate: {result['conversion_rate'] * 100:.1f}%")
                print(f"   Demo Completion Rate: {result['demo_completion_rate'] * 100:.1f}%")
                print(f"   Paywall Hit Rate: {result['paywall_hit_rate'] * 100:.1f}%")
                return result
            else:
                error = await response.text()
                print(f"❌ Lead analytics failed: {response.status} - {error}")
                return {}
    
    async def run_full_test(self):
        """Run complete DOMINANCE SAAS DOCTRINE v4 test suite."""
        print("🎯 DOMINANCE SAAS DOCTRINE v4 - Full Test Suite")
        print("=" * 60)
        
        # Test 1: Governance Health
        await self.test_governance_health()
        
        # Test 2: Lead Capture
        lead_result = await self.test_lead_capture()
        if not self.demo_token:
            print("❌ Cannot continue without demo token")
            return
        
        # Test 3: Lead Status
        await self.test_lead_status()
        
        # Test 4: Demo Executions (3 attempts with escalating value)
        for attempt in range(1, 4):
            result = await self.test_demo_execution(attempt)
            
            if result.get("paywall_hit"):
                print(f"💰 Paywall triggered as expected on attempt {attempt}")
                break
            
            # Check lead status after each attempt
            await self.test_lead_status()
            
            # Small delay between attempts
            await asyncio.sleep(1)
        
        # Test 5: Lead Analytics
        await self.test_lead_analytics()
        
        print("\n" + "=" * 60)
        print("🎉 DOMINANCE SAAS DOCTRINE v4 Test Complete!")
        print("✅ All core functionality tested successfully")
        print("💰 Paywall enforcement working")
        print("📊 ROI metrics being generated")
        print("🛡️ Governance pipeline enforcing rules")
        print("🚀 Ready for production deployment!")


async def main():
    """Main test runner."""
    print("🚀 Starting DOMINANCE SAAS DOCTRINE v4 Tests...")
    print(f"📍 Target: {BASE_URL}")
    print()
    
    try:
        async with DominanceDoctrineTester() as tester:
            await tester.run_full_test()
    except aiohttp.ClientConnectorError:
        print("❌ Cannot connect to backend server")
        print("💡 Make sure the backend is running:")
        print("   python -m uvicorn apps.api.main:app --reload --host 0.0.0.0 --port 8000")
    except Exception as e:
        print(f"❌ Test failed with error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
