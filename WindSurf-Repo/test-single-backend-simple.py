#!/usr/bin/env python
"""
Test script for BYOS Single File Backend - No external dependencies
"""
import urllib.request
import urllib.parse
import json
import time

# Configuration
BASE_URL = "http://localhost:8003"
API_KEYS = {
    "AgencyOS": "agencyos_key_123",
    "BattleArena": "battlearena_key_456", 
    "LumiNode": "luminode_key_789"
}

def make_request(method, url, data=None, headers=None):
    """Make HTTP request using urllib"""
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
        print(f"Request error: {e}")
        return None, str(e)

def test_health():
    """Test health endpoint"""
    try:
        status, data = make_request('GET', f"{BASE_URL}/health")
        print(f"✓ Health check: {status}")
        if status == 200:
            print(f"  Response: {data}")
            return True
        else:
            print(f"  Error: {data}")
            return False
    except Exception as e:
        print(f"✗ Health check failed: {e}")
        return False

def test_status():
    """Test status endpoint"""
    try:
        status, data = make_request('GET', f"{BASE_URL}/status")
        print(f"✓ Status check: {status}")
        if status == 200:
            print(f"  Uptime: {data['uptime_seconds']}s")
            print(f"  Services: DB={data['db_ok']}, Ollama={data['ollama_ok']}")
            print(f"  Active tenants: {data['active_tenants']}")
            print(f"  Total executions: {data['total_executions']}")
            return True
        else:
            print(f"  Error: {data}")
            return False
    except Exception as e:
        print(f"✗ Status check failed: {e}")
        return False

def test_execution(tenant_name, api_key, prompt):
    """Test execution endpoint"""
    try:
        headers = {"X-API-Key": api_key}
        payload = {
            "prompt": prompt,
            "model": "llama3.2:1b"
        }
        
        status, data = make_request('POST', f"{BASE_URL}/v1/exec", payload, headers)
        print(f"✓ {tenant_name} execution: {status}")
        if status == 200:
            print(f"  Tenant ID: {data['tenant_id']}")
            print(f"  Model: {data['model']}")
            print(f"  Tokens: {data['tokens_generated']}")
            print(f"  Time: {data['execution_time_ms']}ms")
            print(f"  Response: {data['response'][:100]}...")
            return True
        else:
            print(f"  Error: {data}")
            return False
            
    except Exception as e:
        print(f"✗ {tenant_name} execution failed: {e}")
        return False

def test_tenant_stats(tenant_name, api_key):
    """Test tenant statistics"""
    try:
        # Get tenant_id from API key
        tenant_id = {
            "agencyos_key_123": "agencyos",
            "battlearena_key_456": "battlearena",
            "luminode_key_789": "luminode"
        }[api_key]
        
        status, data = make_request('GET', f"{BASE_URL}/tenant/{tenant_id}")
        print(f"✓ {tenant_name} stats: {status}")
        if status == 200:
            print(f"  Daily usage: {data['daily_used']}/{data['daily_limit']}")
            print(f"  Total executions: {data['total_executions']}")
            print(f"  Avg time: {data['avg_execution_time_ms']}ms")
            return True
        else:
            print(f"  Error: {data}")
            return False
            
    except Exception as e:
        print(f"✗ {tenant_name} stats failed: {e}")
        return False

def test_invalid_api_key():
    """Test invalid API key"""
    try:
        headers = {"X-API-Key": "invalid_key"}
        payload = {"prompt": "test"}
        
        status, data = make_request('POST', f"{BASE_URL}/v1/exec", payload, headers)
        print(f"✓ Invalid API key test: {status}")
        if status == 401:
            print("  Properly rejected invalid API key")
            return True
        else:
            print(f"  Unexpected response: {data}")
            return False
            
    except Exception as e:
        print(f"✗ Invalid API key test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("BYOS Backend - Single File Approach Tests")
    print("=" * 60)
    
    # Test basic endpoints
    if not test_health():
        print("\n❌ Health check failed - aborting tests")
        return False
    
    print()
    
    if not test_status():
        print("\n❌ Status check failed - aborting tests")
        return False
    
    print()
    
    # Test tenant executions
    test_prompts = {
        "AgencyOS": "What is the best marketing strategy for a SaaS company?",
        "BattleArena": "Create a game concept for a multiplayer battle arena",
        "LumiNode": "Explain the concept of machine learning in simple terms"
    }
    
    passed = 0
    total = len(API_KEYS) + 2  # +2 for invalid key and stats tests
    
    for tenant_name, api_key in API_KEYS.items():
        print(f"--- {tenant_name} ---")
        if test_execution(tenant_name, api_key, test_prompts[tenant_name]):
            passed += 1
        
        if test_tenant_stats(tenant_name, api_key):
            passed += 1
        
        print()
    
    # Test invalid API key
    print("--- Security Test ---")
    if test_invalid_api_key():
        passed += 1
    print()
    
    # Summary
    print("=" * 60)
    print(f"Test Summary: {passed}/{total} passed")
    if passed == total:
        print("🎉 All tests passed - System is ready!")
    else:
        print(f"⚠️  {total - passed} tests failed - Review issues")
    print("=" * 60)
    
    return passed == total

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
