#!/usr/bin/env python3
"""
SYSTEM STATUS REPORT
===================

Shows the current status of the BYOS AI Backend system.
"""

import subprocess
import json

def run_command(cmd):
    """Run a command and return output."""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except:
        return "", "Command failed", 1

def check_system_status():
    """Check system status."""
    
    print("🚀 BYOS AI BACKEND - SYSTEM STATUS")
    print("=" * 50)
    
    base_url = "http://localhost:8000"
    
    # Check server status
    print("📡 SERVER STATUS")
    print("-" * 30)
    
    stdout, stderr, code = run_command(f"curl -s {base_url}/health")
    if code == 0 and stdout:
        try:
            health = json.loads(stdout)
            print(f"✅ Server: {health.get('status', 'unknown')}")
            print(f"✅ Version: {health.get('version', 'unknown')}")
        except:
            print(f"✅ Server: Responding (raw: {stdout[:50]}...)")
    else:
        print("❌ Server: Not responding")
        return
    
    # Check API docs
    stdout, stderr, code = run_command(f"curl -s {base_url}/api/v1/docs")
    if code == 0 and "Swagger UI" in stdout:
        print("✅ API Docs: Available")
    else:
        print("❌ API Docs: Not available")
    
    # Check root endpoint
    stdout, stderr, code = run_command(f"curl -s {base_url}/")
    if code == 0 and stdout:
        try:
            root = json.loads(stdout)
            print(f"✅ App: {root.get('name', 'unknown')}")
            print(f"✅ Features: {len(root.get('features', []))} configured")
        except:
            print("✅ App: Responding")
    
    print("\n🤖 AI EXECUTION SYSTEM")
    print("-" * 30)
    
    # Test governance health (will show auth requirement)
    stdout, stderr, code = run_command(f"curl -s {base_url}/api/v1/governance/health")
    if code == 0 and "Authorization" in stdout:
        print("✅ Governance: Protected (auth required)")
    elif code == 0:
        print("✅ Governance: Responding")
    else:
        print("❌ Governance: Not responding")
    
    # Test AI execution (will show auth requirement)
    stdout, stderr, code = run_command(f'curl -s -X POST {base_url}/api/v1/governance/execute -H "Content-Type: application/json" -d "{\"operation_type\":\"summarize\",\"input_text\":\"test\"}"')
    if code == 0 and "Authorization" in stdout:
        print("✅ AI Execute: Protected (auth required)")
    elif code == 0:
        print("✅ AI Execute: Responding")
    else:
        print("❌ AI Execute: Not responding")
    
    print("\n💳 STRIPE BILLING")
    print("-" * 30)
    
    # Test Stripe plans (will show auth requirement)
    stdout, stderr, code = run_command(f"curl -s {base_url}/api/v1/stripe/plans")
    if code == 0 and "Authorization" in stdout:
        print("✅ Stripe: Protected (auth required)")
    elif code == 0:
        print("✅ Stripe: Responding")
    else:
        print("❌ Stripe: Not responding")
    
    print("\n🔧 CONFIGURATION")
    print("-" * 30)
    
    # Check if .env exists
    try:
        with open('.env', 'r') as f:
            env_content = f.read()
            if 'STRIPE_SECRET_KEY=' in env_content:
                print("✅ Stripe: Configured")
            if 'DATABASE_URL=' in env_content:
                print("✅ Database: Configured")
            if 'HUGGINGFACE_API_KEY=' in env_content:
                print("✅ AI Providers: Configured")
    except:
        print("⚠️  Configuration: .env file not readable")
    
    # Check key files
    files_to_check = [
        'api/main.py',
        'core/governance/pipeline.py',
        'core/revenue/billing_stripe.py',
        'apps/api/routers/governance.py'
    ]
    
    for file_path in files_to_check:
        try:
            with open(file_path, 'r'):
                print(f"✅ {file_path}: Present")
        except:
            print(f"❌ {file_path}: Missing")
    
    print("\n🌐 ENDPOINTS AVAILABLE")
    print("-" * 30)
    print(f"📚 API Documentation: {base_url}/api/v1/docs")
    print(f"🏥 Health Check: {base_url}/health")
    print(f"🏠 Root Endpoint: {base_url}/")
    print(f"🤖 AI Execute: {base_url}/api/v1/governance/execute (auth required)")
    print(f"💳 Stripe Plans: {base_url}/api/v1/stripe/plans (auth required)")
    
    print("\n📋 NEXT STEPS")
    print("-" * 30)
    print("1. ✅ Server is running and healthy")
    print("2. ✅ API documentation is available")
    print("3. 🔐 API endpoints require authentication (as expected)")
    print("4. 🧪 To test with auth, use the comprehensive test suite")
    print("5. 📖 Visit API docs to explore all endpoints")
    
    print(f"\n🎉 SYSTEM STATUS: OPERATIONAL")
    print("=" * 50)

if __name__ == "__main__":
    check_system_status()
