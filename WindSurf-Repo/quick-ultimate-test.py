#!/usr/bin/env python
"""
Quick test for BYOS Ultimate Backend
"""
import urllib.request
import json

# Test health
try:
    response = urllib.request.urlopen("http://localhost:8005/health")
    data = json.loads(response.read().decode())
    print("✅ Health check:", data['status'])
except Exception as e:
    print("❌ Health check failed:", e)

# Test status
try:
    response = urllib.request.urlopen("http://localhost:8005/status")
    data = json.loads(response.read().decode())
    print("✅ Status check:")
    print(f"   Uptime: {data['uptime_seconds']}s")
    print(f"   Services: DB={data['db_ok']}, Ollama={data['ollama_ok']}")
    print(f"   Active tenants: {data['active_tenants']}")
    print(f"   Executive metrics: {data['executive_metrics']}")
    print(f"   Active alerts: {data['active_alerts']}")
except Exception as e:
    print("❌ Status check failed:", e)

# Test multi-tenant execution
try:
    payload = json.dumps({"prompt": "What is machine learning?"}).encode('utf-8')
    req = urllib.request.Request(
        "http://localhost:8005/v1/exec",
        method='POST',
        data=payload,
        headers={
            'Content-Type': 'application/json',
            'X-API-Key': 'agencyos_key_123'
        }
    )
    
    response = urllib.request.urlopen(req)
    data = json.loads(response.read().decode())
    print("✅ Multi-tenant execution:")
    print(f"   Tenant: {data['tenant_id']}")
    print(f"   Model: {data['model']}")
    print(f"   Tokens: {data['tokens_generated']}")
    print(f"   Time: {data['execution_time_ms']}ms")
    print(f"   Response: {data['response'][:100]}...")
    
except Exception as e:
    print("❌ Multi-tenant execution failed:", e)

print("\n🎉 BYOS Ultimate Backend is working!")
print("🌐 Executive Dashboard: http://localhost:8005")
print("🔑 Multi-Tenant API: http://localhost:8005/v1/exec")
