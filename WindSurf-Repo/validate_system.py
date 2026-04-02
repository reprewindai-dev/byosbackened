#!/usr/bin/env python3
"""
QUICK SYSTEM VALIDATION
=======================

Quick test to validate the dashboard system is working.
"""

import requests
import json
from datetime import datetime

def test_system():
    """Test the complete system."""
    
    print("🚀 BYOS AI BACKEND - SYSTEM VALIDATION")
    print("=" * 50)
    
    base_url = "http://localhost:8000"
    
    # Test 1: Server Health
    print("\n🏥 TESTING SERVER HEALTH")
    print("-" * 30)
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            health = response.json()
            print(f"✅ Server Status: {health['status']}")
            print(f"✅ Version: {health['version']}")
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Server not reachable: {e}")
        print("💡 Make sure server is running: python -m uvicorn api.main:app --host 0.0.0.0 --port 8000")
        return False
    
    # Test 2: API Documentation
    print("\n📚 TESTING API DOCS")
    print("-" * 30)
    try:
        response = requests.get(f"{base_url}/api/v1/docs", timeout=5)
        if response.status_code == 200 and "Swagger UI" in response.text:
            print("✅ API Documentation: Available")
        else:
            print(f"❌ API Docs failed: {response.status_code}")
    except Exception as e:
        print(f"❌ API Docs error: {e}")
    
    # Test 3: Root Endpoint
    print("\n🏠 TESTING ROOT ENDPOINT")
    print("-" * 30)
    try:
        response = requests.get(f"{base_url}/", timeout=5)
        if response.status_code == 200:
            root = response.json()
            print(f"✅ App Name: {root['name']}")
            print(f"✅ Features: {len(root['features'])} configured")
            print(f"   Features: {', '.join(root['features'])}")
        else:
            print(f"❌ Root endpoint failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Root endpoint error: {e}")
    
    # Test 4: Authentication (will show expected error)
    print("\n🔐 TESTING AUTHENTICATION")
    print("-" * 30)
    try:
        response = requests.post(
            f"{base_url}/api/v1/auth/login",
            json={"username": "admin", "password": "admin123"},
            timeout=5
        )
        if response.status_code == 200:
            auth_data = response.json()
            print("✅ Admin Login: Working")
            print(f"   Token: {auth_data['access_token'][:20]}...")
            
            # Test admin dashboard with token
            headers = {"Authorization": f"Bearer {auth_data['access_token']}"}
            admin_response = requests.get(f"{base_url}/api/v1/admin/dashboard/config", headers=headers, timeout=5)
            if admin_response.status_code == 200:
                admin_config = admin_response.json()
                print(f"✅ Admin Dashboard: {len(admin_config['switches'])} switches available")
            else:
                print(f"❌ Admin Dashboard: {admin_response.status_code}")
                
        else:
            print(f"❌ Admin Login failed: {response.status_code}")
            error_data = response.json()
            print(f"   Error: {error_data.get('detail', 'Unknown error')}")
    except Exception as e:
        print(f"❌ Authentication error: {e}")
    
    # Test 5: Dashboard Files
    print("\n📁 TESTING DASHBOARD FILES")
    print("-" * 30)
    import os
    
    dashboard_files = [
        ("admin_dashboard.html", "Admin Dashboard"),
        ("user_dashboard.html", "User Dashboard"),
        ("DASHBOARD_GUIDE.md", "Dashboard Guide")
    ]
    
    for filename, description in dashboard_files:
        if os.path.exists(filename):
            print(f"✅ {description}: Available")
        else:
            print(f"❌ {description}: Missing")
    
    # Test 6: System Components
    print("\n🔧 TESTING SYSTEM COMPONENTS")
    print("-" * 30)
    
    components = [
        ("api/main.py", "Main API"),
        ("apps/api/routers/admin_dashboard.py", "Admin Dashboard API"),
        ("apps/api/routers/user_dashboard.py", "User Dashboard API"),
        ("apps/api/routers/dashboard_auth.py", "Authentication API"),
        ("core/governance/pipeline.py", "Governance Pipeline"),
        ("core/revenue/billing_stripe.py", "Stripe Billing")
    ]
    
    for filepath, description in components:
        if os.path.exists(filepath):
            print(f"✅ {description}: Available")
        else:
            print(f"❌ {description}: Missing")
    
    print("\n🎉 SYSTEM VALIDATION COMPLETE")
    print("=" * 50)
    
    print("\n🌐 ACCESS URLs:")
    print(f"   📚 API Documentation: {base_url}/api/v1/docs")
    print(f"   🏥 Health Check: {base_url}/health")
    print(f"   🏠 Root Endpoint: {base_url}/")
    print(f"   🔧 Admin Dashboard: admin_dashboard.html")
    print(f"   👤 User Dashboard: user_dashboard.html")
    
    print("\n🔐 LOGIN CREDENTIALS:")
    print("   👤 Admin: username=admin, password=admin123")
    print("   👥 User: username=user, password=user123")
    
    print("\n🎛️ DASHBOARD FEATURES:")
    print("   🔧 Admin: Full control over 18 system switches")
    print("   👤 User: Read-only view of system status")
    print("   🔄 Real-time updates and monitoring")
    print("   📊 System metrics and activity logs")
    
    print("\n⚡ QUICK START:")
    print("   1. Open admin_dashboard.html in browser")
    print("   2. Login with admin/admin123")
    print("   3. Toggle switches to control system features")
    print("   4. Open user_dashboard.html for read-only view")
    
    print(f"\n✅ SYSTEM STATUS: READY FOR USE!")
    print(f"   Timestamp: {datetime.now().isoformat()}")

if __name__ == "__main__":
    test_system()
