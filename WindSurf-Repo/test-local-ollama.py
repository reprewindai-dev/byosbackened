#!/usr/bin/env python
"""
Test script for BYOS Backend - Local Ollama Setup
"""
import requests
import json
import time
import uuid

# Configuration
BASE_URL = "http://localhost:8000"
API_KEYS = {
    "AgencyOS": "agencyos_key_123",
    "BattleArena": "battlearena_key_456", 
    "LumiNode": "luminode_key_789"
}

def test_health():
    """Test health endpoint"""
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"✓ Health check: {response.status_code}")
        print(f"  Response: {response.json()}")
        return True
    except Exception as e:
        print(f"✗ Health check failed: {e}")
        return False

def test_status():
    """Test status endpoint"""
    try:
        response = requests.get(f"{BASE_URL}/status")
        print(f"✓ Status check: {response.status_code}")
        data = response.json()
        print(f"  Uptime: {data['uptime_seconds']}s")
        print(f"  Services: DB={data['db_ok']}, Redis={data['redis_ok']}, LLM={data['llm_ok']}")
        print(f"  Active tenants: {data['active_tenants']}")
        print(f"  Total executions: {data['total_executions']}")
        return True
    except Exception as e:
        print(f"✗ Status check failed: {e}")
        return False

def test_execution(tenant_name, api_key, prompt):
    """Test execution endpoint"""
    try:
        headers = {"X-API-Key": api_key}
        payload = {
            "prompt": prompt,
            "model": "llama3.2:1b",
            "stream": False
        }
        
        response = requests.post(
            f"{BASE_URL}/v1/exec",
            headers=headers,
            json=payload
        )
        
        print(f"✓ {tenant_name} execution: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  Tenant ID: {data['tenant_id']}")
            print(f"  Model: {data['model']}")
            print(f"  Tokens: {data['tokens_generated']}")
            print(f"  Time: {data['execution_time_ms']}ms")
            print(f"  Response: {data['response'][:100]}...")
            return True
        else:
            print(f"  Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"✗ {tenant_name} execution failed: {e}")
        return False

def test_invalid_api_key():
    """Test invalid API key"""
    try:
        headers = {"X-API-Key": "invalid_key"}
        payload = {"prompt": "test"}
        
        response = requests.post(
            f"{BASE_URL}/v1/exec",
            headers=headers,
            json=payload
        )
        
        print(f"✓ Invalid API key test: {response.status_code}")
        if response.status_code == 401:
            print("  Properly rejected invalid API key")
            return True
        else:
            print(f"  Unexpected response: {response.text}")
            return False
            
    except Exception as e:
        print(f"✗ Invalid API key test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("BYOS Backend - Local Ollama Setup Tests")
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
    total = len(API_KEYS) + 1  # +1 for invalid key test
    
    for tenant_name, api_key in API_KEYS.items():
        print(f"--- {tenant_name} ---")
        if test_execution(tenant_name, api_key, test_prompts[tenant_name]):
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
