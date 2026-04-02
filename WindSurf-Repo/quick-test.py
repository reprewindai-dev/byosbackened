#!/usr/bin/env python
"""
Quick test for BYOS Backend
"""
import urllib.request
import json

# Test execution
try:
    data = json.dumps({"prompt": "What is machine learning?"}).encode('utf-8')
    req = urllib.request.Request(
        "http://localhost:8003/v1/exec",
        method='POST',
        data=data,
        headers={
            'Content-Type': 'application/json',
            'X-API-Key': 'agencyos_key_123'
        }
    )
    
    with urllib.request.urlopen(req) as response:
        result = json.loads(response.read().decode('utf-8'))
        print("✅ Execution successful!")
        print(f"Response: {result['response'][:200]}...")
        print(f"Tenant: {result['tenant_id']}")
        print(f"Time: {result['execution_time_ms']}ms")
        
except Exception as e:
    print(f"❌ Error: {e}")
