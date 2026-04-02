#!/usr/bin/env python
"""
Smoke tests for BYOS AI Backend Executive Dashboard
"""
import requests
import json
import sys
from datetime import datetime

BASE_URL = "http://localhost:8001"

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

def test_login():
    """Test authentication endpoint"""
    try:
        payload = {
            "username": "admin",
            "password": "admin123"
        }
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        print(f"✓ Login: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  Token received: {data['access_token'][:20]}...")
            return data['access_token']
        else:
            print(f"  Error: {response.text}")
            return None
    except Exception as e:
        print(f"✗ Login failed: {e}")
        return None

def test_executive_overview(token):
    """Test executive overview endpoint"""
    try:
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        response = requests.get(
            f"{BASE_URL}/api/v1/executive/dashboard/overview",
            headers=headers
        )
        print(f"✓ Executive overview: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  Net profit: ${data['executive_summary']['net_profit']:,.2f}")
            print(f"  Gross margin: {data['executive_summary']['gross_margin_percent']}%")
            print(f"  Run rate: ${data['executive_summary']['run_rate']:,.2f}")
            print(f"  Alerts: {len(data['alerts'])} active")
            return True
        else:
            print(f"  Error: {response.text}")
            return False
    except Exception as e:
        print(f"✗ Executive overview failed: {e}")
        return False

def test_guardrails(token):
    """Test guardrails endpoints"""
    try:
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        # Get guardrails
        response = requests.get(
            f"{BASE_URL}/api/v1/executive/dashboard/controls/guardrails",
            headers=headers
        )
        print(f"✓ Get guardrails: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
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
            
            response = requests.post(
                f"{BASE_URL}/api/v1/executive/dashboard/controls/guardrails",
                headers=headers,
                json=update_payload
            )
            print(f"✓ Update guardrails: {response.status_code}")
            return True
        else:
            print(f"  Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"✗ Guardrails test failed: {e}")
        return False

def test_pricing_adjustment(token):
    """Test pricing adjustment endpoint"""
    try:
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "tier": "PRO",
            "adjustment_type": "percentage_increase",
            "percentage_change": 5.0
        }
        
        response = requests.post(
            f"{BASE_URL}/api/v1/executive/dashboard/pricing/adjust",
            headers=headers,
            json=payload
        )
        print(f"✓ Pricing adjustment: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  Status: {data['status']}")
            return True
        else:
            print(f"  Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"✗ Pricing adjustment failed: {e}")
        return False

def test_api_status(token):
    """Test API status endpoint"""
    try:
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        response = requests.get(
            f"{BASE_URL}/api/v1/status",
            headers=headers
        )
        print(f"✓ API status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  Overall status: {data['status']}")
            services = data['services']
            for service, status in services.items():
                print(f"  {service}: {status}")
            return True
        else:
            print(f"  Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"✗ API status test failed: {e}")
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
        print("\n❌ Health check failed - aborting tests")
        sys.exit(1)
    
    print()
    
    # Test authentication
    token = test_login()
    if not token:
        print("\n❌ Authentication failed - aborting tests")
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
        print("🎉 All tests passed - System is production ready!")
    else:
        print(f"⚠️  {total - passed} tests failed - Review issues before production")
    print("=" * 60)
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
