#!/usr/bin/env python3
"""Simple test for DOMINANCE SAAS DOCTRINE v4."""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_health():
    """Test basic health endpoint."""
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"Health: {response.status_code} - {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Health failed: {e}")
        return False

def test_lead_capture():
    """Test lead capture."""
    try:
        data = {
            "email": "test@example.com",
            "company": "Test Corp",
            "use_case": "content_creation",
            "name": "Test User"
        }
        response = requests.post(f"{BASE_URL}/api/v1/leads/capture", json=data)
        print(f"Lead Capture: {response.status_code} - {response.json()}")
        
        if response.status_code == 200:
            result = response.json()
            return result.get("demo_token")
        return None
    except Exception as e:
        print(f"Lead capture failed: {e}")
        return None

def test_demo_execution(demo_token):
    """Test demo execution."""
    try:
        data = {
            "operation_type": "summarize",
            "input_text": "This is a test article that needs to be summarized.",
            "demo_token": demo_token
        }
        response = requests.post(f"{BASE_URL}/api/v1/ai/execute", json=data)
        print(f"Demo Execution: {response.status_code} - {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"Demo execution failed: {e}")
        return False

def main():
    print("🚀 Simple DOMINANCE SAAS DOCTRINE v4 Test")
    print("=" * 50)
    
    # Test 1: Health
    if not test_health():
        print("❌ Server not responding")
        return
    
    # Test 2: Lead Capture
    demo_token = test_lead_capture()
    if not demo_token:
        print("❌ Lead capture failed")
        return
    
    # Test 3: Demo Execution
    if test_demo_execution(demo_token):
        print("✅ Demo execution successful!")
    else:
        print("❌ Demo execution failed")
    
    print("=" * 50)
    print("Test complete!")

if __name__ == "__main__":
    main()
