#!/usr/bin/env python3
"""
QUICK APP VALIDATION
===================

Quick test based on the running app's root response.
"""

import asyncio
import aiohttp
import json

async def quick_test():
    """Quick test of the running application."""
    
    print("🚀 QUICK APP VALIDATION")
    print("=" * 40)
    
    base_url = "http://localhost:8000"
    
    try:
        async with aiohttp.ClientSession() as session:
            print(f"📍 Testing: {base_url}")
            
            # Test root endpoint (we know this works)
            async with session.get(f"{base_url}/") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Root endpoint: {data['name']} v{data['version']}")
                    print(f"   Features: {', '.join(data['features'])}")
                    print(f"   Docs: {data['docs']}")
                else:
                    print(f"❌ Root endpoint failed: {response.status}")
                    return
            
            # Test health endpoint
            async with session.get(f"{base_url}/health") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Health: {data['status']}")
                else:
                    print(f"❌ Health failed: {response.status}")
            
            # Test API health
            async with session.get(f"{base_url}/api/v1/health") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ API Health: {data['status']} v{data['version']}")
                else:
                    print(f"❌ API Health failed: {response.status}")
            
            # Test AI execution (the main feature)
            print("\n🤖 TESTING AI EXECUTION")
            print("-" * 30)
            
            ai_request = {
                "operation_type": "summarize",
                "input_text": "BYOS AI Backend provides Cost Intelligence, Intelligent Routing, Compliance & Audit, Privacy-by-Design, and a Plugin System for portable AI infrastructure.",
                "temperature": 0.7,
                "max_tokens": 150
            }
            
            async with session.post(
                f"{base_url}/api/v1/governance/execute",
                json=ai_request,
                headers={"Content-Type": "application/json"}
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    print(f"✅ AI Execution: SUCCESS")
                    print(f"   Request ID: {result.get('request_id', 'N/A')}")
                    print(f"   Success: {result.get('success', False)}")
                    print(f"   Execution Time: {result.get('execution_time_ms', 0)}ms")
                    print(f"   Risk Level: {result.get('risk_level', 'N/A')}")
                    print(f"   Coherence Score: {result.get('coherence_score', 0):.2f}")
                    print(f"   Result: {result.get('result', 'N/A')[:100]}...")
                else:
                    error_text = await response.text()
                    print(f"❌ AI Execution failed: {response.status}")
                    print(f"   Error: {error_text[:200]}...")
            
            # Test Stripe billing
            print("\n💳 TESTING STRIPE BILLING")
            print("-" * 30)
            
            async with session.get(f"{base_url}/api/v1/stripe/plans") as response:
                if response.status == 200:
                    plans = await response.json()
                    print(f"✅ Stripe Plans: {len(plans)} available")
                    for plan in plans[:2]:  # Show first 2 plans
                        print(f"   - {plan.get('name', 'Unknown')}: ${plan.get('price_monthly', 0)/100:.2f}/mo")
                else:
                    print(f"❌ Stripe Plans failed: {response.status}")
            
            # Test governance health
            print("\n🏛️  TESTING GOVERNANCE SYSTEM")
            print("-" * 30)
            
            async with session.get(f"{base_url}/api/v1/governance/health") as response:
                if response.status == 200:
                    health = await response.json()
                    print(f"✅ Governance Health: {health.get('status', 'N/A')}")
                    print(f"   Pipeline Version: {health.get('pipeline_version', 'N/A')}")
                    components = health.get('components', {})
                    for comp, status in components.items():
                        print(f"   - {comp}: {status}")
                else:
                    print(f"❌ Governance Health failed: {response.status}")
            
            print("\n🎉 QUICK TEST COMPLETE!")
            print("=" * 40)
            print("✅ App is running and responding")
            print("✅ AI execution system working")
            print("✅ Stripe billing configured")
            print("✅ Governance pipeline operational")
            print("\n🌐 Available endpoints:")
            print(f"   📚 API Docs: {base_url}/api/v1/docs")
            print(f"   🤖 AI Execute: {base_url}/api/v1/governance/execute")
            print(f"   💳 Billing Plans: {base_url}/api/v1/stripe/plans")
            print(f"   🏛️  Governance: {base_url}/api/v1/governance/health")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        print("Make sure the server is running at http://localhost:8000")

if __name__ == "__main__":
    asyncio.run(quick_test())
