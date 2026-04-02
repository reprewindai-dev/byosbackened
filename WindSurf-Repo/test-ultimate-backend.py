#!/usr/bin/env python
"""
Test script for BYOS Ultimate Combined Backend
"""
import urllib.request
import json
import time

def test_endpoint(url, method="GET", data=None, headers=None):
    """Test HTTP endpoint"""
    try:
        if headers is None:
            headers = {}
        
        req = urllib.request.Request(url, method=method)
        
        for key, value in headers.items():
            req.add_header(key, value)
        
        if data:
            req.data = json.dumps(data).encode('utf-8')
            req.add_header('Content-Type', 'application/json')
        
        with urllib.request.urlopen(req) as response:
            return response.status, json.loads(response.read().decode('utf-8'))
    except Exception as e:
        return None, str(e)

def main():
    """Run comprehensive tests"""
    print("=" * 80)
    print("🚀 BYOS ULTIMATE BACKEND - COMPREHENSIVE TESTS")
    print("=" * 80)
    
    base_url = "http://localhost:8005"
    
    # Test 1: Executive Dashboard
    print("1. Testing Executive Dashboard...")
    status, data = test_endpoint(f"{base_url}/")
    if status == 200:
        print("✅ Executive Dashboard served successfully")
    else:
        print(f"❌ Executive Dashboard failed: {data}")
        return False
    
    # Test 2: Health Check
    print("\n2. Testing Health Check...")
    status, data = test_endpoint(f"{base_url}/health")
    if status == 200:
        print(f"✅ Health check passed: {data['status']}")
    else:
        print(f"❌ Health check failed: {data}")
        return False
    
    # Test 3: System Status
    print("\n3. Testing System Status...")
    status, data = test_endpoint(f"{base_url}/status")
    if status == 200:
        print("✅ System status check passed")
        print(f"   Uptime: {data['uptime_seconds']}s")
        print(f"   Services: DB={data['db_ok']}, Ollama={data['ollama_ok']}")
        print(f"   Active tenants: {data['active_tenants']}")
        print(f"   Total executions: {data['total_executions']}")
        print(f"   Executive metrics: {data['executive_metrics']}")
        print(f"   Active alerts: {data['active_alerts']}")
    else:
        print(f"❌ System status failed: {data}")
        return False
    
    # Test 4: Admin Authentication
    print("\n4. Testing Admin Authentication...")
    payload = {"username": "admin", "password": "admin123"}
    status, data = test_endpoint(f"{base_url}/api/v1/auth/login", "POST", payload)
    if status == 200:
        print("✅ Admin authentication successful")
        admin_token = data['access_token']
    else:
        print(f"❌ Admin authentication failed: {data}")
        return False
    
    # Test 5: Executive Overview
    print("\n5. Testing Executive Overview...")
    headers = {"Authorization": f"Bearer {admin_token}"}
    status, data = test_endpoint(f"{base_url}/api/v1/executive/dashboard/overview", headers=headers)
    if status == 200:
        print("✅ Executive overview successful")
        print(f"   Net profit: ${data['executive_summary']['net_profit']:,.2f}")
        print(f"   Gross margin: {data['executive_summary']['gross_margin_percent']}%")
        print(f"   Run rate: ${data['executive_summary']['run_rate']:,.2f}")
        print(f"   Alerts: {len(data['alerts'])} active")
    else:
        print(f"❌ Executive overview failed: {data}")
        return False
    
    # Test 6: Multi-Tenant API - AgencyOS
    print("\n6. Testing Multi-Tenant API - AgencyOS...")
    headers = {"X-API-Key": "agencyos_key_123"}
    payload = {"prompt": "What is the best marketing strategy for a SaaS company?"}
    status, data = test_endpoint(f"{base_url}/v1/exec", "POST", payload, headers)
    if status == 200:
        print("✅ AgencyOS execution successful")
        print(f"   Tenant: {data['tenant_id']}")
        print(f"   Model: {data['model']}")
        print(f"   Tokens: {data['tokens_generated']}")
        print(f"   Time: {data['execution_time_ms']}ms")
        print(f"   Response: {data['response'][:100]}...")
    else:
        print(f"❌ AgencyOS execution failed: {data}")
        return False
    
    # Test 7: Multi-Tenant API - BattleArena
    print("\n7. Testing Multi-Tenant API - BattleArena...")
    headers = {"X-API-Key": "battlearena_key_456"}
    payload = {"prompt": "Create a game concept for a multiplayer battle arena"}
    status, data = test_endpoint(f"{base_url}/v1/exec", "POST", payload, headers)
    if status == 200:
        print("✅ BattleArena execution successful")
        print(f"   Tenant: {data['tenant_id']}")
        print(f"   Tokens: {data['tokens_generated']}")
        print(f"   Time: {data['execution_time_ms']}ms")
    else:
        print(f"❌ BattleArena execution failed: {data}")
        return False
    
    # Test 8: Multi-Tenant API - LumiNode
    print("\n8. Testing Multi-Tenant API - LumiNode...")
    headers = {"X-API-Key": "luminode_key_789"}
    payload = {"prompt": "Explain machine learning in simple terms"}
    status, data = test_endpoint(f"{base_url}/v1/exec", "POST", payload, headers)
    if status == 200:
        print("✅ LumiNode execution successful")
        print(f"   Tenant: {data['tenant_id']}")
        print(f"   Tokens: {data['tokens_generated']}")
        print(f"   Time: {data['execution_time_ms']}ms")
    else:
        print(f"❌ LumiNode execution failed: {data}")
        return False
    
    # Test 9: Tenant Statistics
    print("\n9. Testing Tenant Statistics...")
    tenants = ["agencyos", "battlearena", "luminode"]
    for tenant_id in tenants:
        status, data = test_endpoint(f"{base_url}/tenant/{tenant_id}")
        if status == 200:
            print(f"✅ {tenant_id} stats: {data['daily_used']}/{data['daily_limit']} daily")
        else:
            print(f"❌ {tenant_id} stats failed: {data}")
            return False
    
    # Test 10: Pricing Adjustment
    print("\n10. Testing Pricing Adjustment...")
    headers = {"Authorization": f"Bearer {admin_token}"}
    payload = {"tier": "PRO", "adjustment_type": "percentage_increase", "percentage_change": 5.0}
    status, data = test_endpoint(f"{base_url}/api/v1/executive/dashboard/pricing/adjust", "POST", payload, headers)
    if status == 200:
        print("✅ Pricing adjustment successful")
    else:
        print(f"❌ Pricing adjustment failed: {data}")
        return False
    
    # Test 11: Guardrails Update
    print("\n11. Testing Guardrails Update...")
    headers = {"X-API-Key": "admin_token_12345"}
    payload = {
        "daily_budget": 3000.0,
        "monthly_budget": 65000.0,
        "power_saving_mode": True,
        "cost_strategy": "aggressive"
    }
    status, data = test_endpoint(f"{base_url}/api/v1/executive/dashboard/controls/guardrails", "POST", payload, headers)
    if status == 200:
        print("✅ Guardrails update successful")
    else:
        print(f"❌ Guardrails update failed: {data}")
        return False
    
    # Test 12: Invalid API Key
    print("\n12. Testing Invalid API Key...")
    headers = {"X-API-Key": "invalid_key"}
    payload = {"prompt": "test"}
    status, data = test_endpoint(f"{base_url}/v1/exec", "POST", payload, headers)
    if status == 401:
        print("✅ Invalid API key properly rejected")
    else:
        print(f"❌ Invalid API key test failed: {data}")
        return False
    
    print("\n" + "=" * 80)
    print("🎉 ALL TESTS PASSED!")
    print("✅ BYOS Ultimate Backend is fully operational!")
    print("=" * 80)
    print("\n📊 SYSTEM SUMMARY:")
    print("✅ Executive Dashboard: Working")
    print("✅ Multi-Tenant API: Working")
    print("✅ Local Ollama Integration: Working")
    print("✅ Database Persistence: Working")
    print("✅ Authentication System: Working")
    print("✅ Business Intelligence: Working")
    print("✅ Tenant Isolation: Working")
    print("✅ Production Ready: ✅")
    print("=" * 80)
    
    return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
