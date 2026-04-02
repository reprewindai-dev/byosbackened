#!/usr/bin/env python
"""
Test script for BYOS Zero Dependencies Backend
"""
import urllib.request
import json

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
    """Run tests"""
    print("=" * 60)
    print("BYOS Zero Dependencies Backend Tests")
    print("=" * 60)
    
    base_url = "http://localhost:8004"
    
    # Test health
    print("1. Testing health endpoint...")
    status, data = test_endpoint(f"{base_url}/health")
    if status == 200:
        print(f"✅ Health check passed: {data['status']}")
    else:
        print(f"❌ Health check failed: {data}")
        return False
    
    # Test status
    print("\n2. Testing status endpoint...")
    status, data = test_endpoint(f"{base_url}/status")
    if status == 200:
        print(f"✅ Status check passed")
        print(f"   Uptime: {data['uptime_seconds']}s")
        print(f"   Services: DB={data['db_ok']}, Ollama={data['ollama_ok']}")
        print(f"   Active tenants: {data['active_tenants']}")
    else:
        print(f"❌ Status check failed: {data}")
        return False
    
    # Test execution
    print("\n3. Testing execution endpoint...")
    headers = {"X-API-Key": "agencyos_key_123"}
    payload = {"prompt": "What is machine learning?"}
    
    status, data = test_endpoint(f"{base_url}/v1/exec", "POST", payload, headers)
    if status == 200:
        print(f"✅ Execution test passed")
        print(f"   Tenant: {data['tenant_id']}")
        print(f"   Model: {data['model']}")
        print(f"   Tokens: {data['tokens_generated']}")
        print(f"   Time: {data['execution_time_ms']}ms")
        print(f"   Response: {data['response'][:100]}...")
    else:
        print(f"❌ Execution test failed: {data}")
        return False
    
    # Test tenant stats
    print("\n4. Testing tenant stats...")
    status, data = test_endpoint(f"{base_url}/tenant/agencyos")
    if status == 200:
        print(f"✅ Tenant stats passed")
        print(f"   Daily usage: {data['daily_used']}/{data['daily_limit']}")
        print(f"   Total executions: {data['total_executions']}")
    else:
        print(f"❌ Tenant stats failed: {data}")
        return False
    
    # Test invalid API key
    print("\n5. Testing invalid API key...")
    headers = {"X-API-Key": "invalid_key"}
    payload = {"prompt": "test"}
    
    status, data = test_endpoint(f"{base_url}/v1/exec", "POST", payload, headers)
    if status == 401:
        print("✅ Invalid API key properly rejected")
    else:
        print(f"❌ Invalid API key test failed: {data}")
        return False
    
    print("\n" + "=" * 60)
    print("🎉 ALL TESTS PASSED!")
    print("✅ BYOS Zero Dependencies Backend is ready!")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    main()
