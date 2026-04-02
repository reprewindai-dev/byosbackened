#!/usr/bin/env python
"""
Smoke tests for BYOS AI Backend Executive Dashboard
Using only standard library
"""
import urllib.request
import urllib.parse
import json
import sys
from datetime import datetime

BASE_URL = "http://localhost:8001"

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
        print(f"[PASS] Health check: {status}")
        if status == 200:
            print(f"  Response: {data}")
            return True
        else:
            print(f"  Error: {data}")
            return False
    except Exception as e:
        print(f"[FAIL] Health check failed: {e}")
        return False

def test_login():
    """Test authentication endpoint"""
    try:
        payload = {
            "username": "admin",
            "password": "admin123"
        }
        status, data = make_request('POST', f"{BASE_URL}/api/v1/auth/login", payload)
        print(f"[PASS] Login: {status}")
        if status == 200:
            print(f"  Token received: {data['access_token'][:20]}...")
            return data['access_token']
        else:
            print(f"  Error: {data}")
            return None
    except Exception as e:
        print(f"[FAIL] Login failed: {e}")
        return None

def test_executive_overview(token):
    """Test executive overview endpoint"""
    try:
        headers = {
            "Authorization": f"Bearer {token}"
        }
        status, data = make_request('GET', f"{BASE_URL}/api/v1/executive/dashboard/overview", headers=headers)
        print(f"[PASS] Executive overview: {status}")
        if status == 200:
            print(f"  Net profit: ${data['executive_summary']['net_profit']:,.2f}")
            print(f"  Gross margin: {data['executive_summary']['gross_margin_percent']}%")
            print(f"  Run rate: ${data['executive_summary']['run_rate']:,.2f}")
            print(f"  Alerts: {len(data['alerts'])} active")
            return True
        else:
            print(f"  Error: {data}")
            return False
    except Exception as e:
        print(f"[FAIL] Executive overview failed: {e}")
        return False

def test_guardrails(token):
    """Test guardrails endpoints"""
    try:
        headers = {
            "Authorization": f"Bearer {token}"
        }
        
        # Get guardrails
        status, data = make_request('GET', f"{BASE_URL}/api/v1/executive/dashboard/controls/guardrails", headers=headers)
        print(f"[PASS] Get guardrails: {status}")
        
        if status == 200:
            print(f"  Daily budget: ${data['daily_budget']:,.2f}")
            print(f"  Monthly budget: ${data['monthly_budget']:,.2f}")
            
            # Update guardrails
            update_payload = {
                "daily_budget": 3000.0,
                "monthly_budget": 65000.0,
                "power_saving_mode": True,
                "provider_spend_caps": {
                    "openai": 25000,
                    "huggingface": 6000,
                    "local": 2000
                },
                "pricing_floor_margin": 35.0,
                "cost_strategy": "aggressive"
            }
            
            status, data = make_request('POST', f"{BASE_URL}/api/v1/executive/dashboard/controls/guardrails", update_payload, headers)
            print(f"[PASS] Update guardrails: {status}")
            return True
        else:
            print(f"  Error: {data}")
            return False
            
    except Exception as e:
        print(f"[FAIL] Guardrails test failed: {e}")
        return False

def test_pricing_adjustment(token):
    """Test pricing adjustment endpoint"""
    try:
        headers = {
            "Authorization": f"Bearer {token}"
        }
        
        payload = {
            "tier": "PRO",
            "adjustment_type": "percentage_increase",
            "percentage_change": 5.0
        }
        
        status, data = make_request('POST', f"{BASE_URL}/api/v1/executive/dashboard/pricing/adjust", payload, headers)
        print(f"[PASS] Pricing adjustment: {status}")
        if status == 200:
            print(f"  Status: {data['status']}")
            return True
        else:
            print(f"  Error: {data}")
            return False
            
    except Exception as e:
        print(f"[FAIL] Pricing adjustment failed: {e}")
        return False

def test_api_status(token):
    """Test API status endpoint"""
    try:
        headers = {
            "Authorization": f"Bearer {token}"
        }
        
        status, data = make_request('GET', f"{BASE_URL}/api/v1/status", headers=headers)
        print(f"[PASS] API status: {status}")
        if status == 200:
            print(f"  Overall status: {data['status']}")
            services = data['services']
            for service, status_val in services.items():
                print(f"  {service}: {status_val}")
            return True
        else:
            print(f"  Error: {data}")
            return False
            
    except Exception as e:
        print(f"[FAIL] API status test failed: {e}")
        return False

def main():
    """Run all smoke tests"""
    print("=" * 60)
    print("BYOS AI Backend - Executive Dashboard Smoke Tests")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Base URL: {BASE_URL}")
    print()
    
    # Test health check
    if not test_health():
        print("\n[ERROR] Health check failed - aborting tests")
        sys.exit(1)
    
    print()
    
    # Test authentication
    token = test_login()
    if not token:
        print("\n[ERROR] Authentication failed - aborting tests")
        sys.exit(1)
    
    print()
    
    # Test all endpoints
    tests = [
        ("Executive Overview", lambda: test_executive_overview(token)),
        ("Guardrails", lambda: test_guardrails(token)),
        ("Pricing Adjustment", lambda: test_pricing_adjustment(token)),
        ("API Status", lambda: test_api_status(token))
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        if test_func():
            passed += 1
        print()
    
    # Summary
    print("=" * 60)
    print(f"Smoke Tests Summary: {passed}/{total} passed")
    if passed == total:
        print("[SUCCESS] All tests passed - System is production ready!")
    else:
        print(f"[WARNING] {total - passed} tests failed - Review issues before production")
    print("=" * 60)
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
