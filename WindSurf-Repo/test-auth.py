#!/usr/bin/env python
"""
Test authentication endpoint directly
"""
import urllib.request
import json

def test_auth():
    try:
        # Test login endpoint
        payload = {
            "username": "admin",
            "password": "admin123"
        }
        
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            "http://localhost:8001/api/v1/auth/login",
            method='POST',
            data=data,
            headers={'Content-Type': 'application/json'}
        )
        
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode('utf-8'))
            print(f"Status: {response.status}")
            print(f"Response: {result}")
            return result
            
    except Exception as e:
        print(f"Auth test failed: {e}")
        return None

if __name__ == "__main__":
    test_auth()
