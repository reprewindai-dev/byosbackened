#!/usr/bin/env python3
"""
Dashboard System Test Script
==============================

Tests the complete dashboard system including authentication,
admin controls, and user read-only access.
"""

import asyncio
import aiohttp
import json
from datetime import datetime

class DashboardTester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = None
        self.admin_token = None
        self.user_token = None
        self.test_results = []
        
    async def setup(self):
        """Setup test session."""
        self.session = aiohttp.ClientSession()
        print(f"🧪 Testing dashboard system at: {self.base_url}")
        
    async def cleanup(self):
        """Cleanup test session."""
        if self.session:
            await self.session.close()
            
    def log_test(self, test_name: str, success: bool, details: str = ""):
        """Log test result."""
        status = "✅ PASS" if success else "❌ FAIL"
        self.test_results.append({
            "test": test_name,
            "status": status,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })
        print(f"{status}: {test_name}")
        if details:
            print(f"    {details}")
            
    async def test_authentication(self):
        """Test authentication system."""
        print("\n🔐 TESTING AUTHENTICATION")
        print("=" * 40)
        
        try:
            # Test admin login
            print("👤 Testing admin login...")
            admin_login = {
                "username": "admin",
                "password": "admin123"
            }
            
            async with self.session.post(
                f"{self.base_url}/api/v1/auth/login",
                json=admin_login,
                headers={"Content-Type": "application/json"}
            ) as response:
                
                if response.status == 200:
                    login_data = await response.json()
                    self.admin_token = login_data["access_token"]
                    self.log_test("Admin login", True, f"Token: {self.admin_token[:20]}...")
                else:
                    error_text = await response.text()
                    self.log_test("Admin login", False, f"Status: {response.status}")
                    return
            
            # Test user login
            print("👥 Testing user login...")
            user_login = {
                "username": "user",
                "password": "user123"
            }
            
            async with self.session.post(
                f"{self.base_url}/api/v1/auth/login",
                json=user_login,
                headers={"Content-Type": "application/json"}
            ) as response:
                
                if response.status == 200:
                    login_data = await response.json()
                    self.user_token = login_data["access_token"]
                    self.log_test("User login", True, f"Token: {self.user_token[:20]}...")
                else:
                    error_text = await response.text()
                    self.log_test("User login", False, f"Status: {response.status}")
                    
        except Exception as e:
            self.log_test("Authentication", False, str(e))
            
    async def test_admin_dashboard(self):
        """Test admin dashboard functionality."""
        print("\n🔧 TESTING ADMIN DASHBOARD")
        print("=" * 40)
        
        if not self.admin_token:
            self.log_test("Admin dashboard", False, "No admin token available")
            return
            
        try:
            # Test admin dashboard config
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            
            async with self.session.get(
                f"{self.base_url}/api/v1/admin/dashboard/config",
                headers=headers
            ) as response:
                
                if response.status == 200:
                    config = await response.json()
                    self.log_test("Admin config", True, f"Switches: {len(config['switches'])}")
                    
                    # Test switches endpoint
                    async with self.session.get(
                        f"{self.base_url}/api/v1/admin/dashboard/switches",
                        headers=headers
                    ) as response:
                        
                        if response.status == 200:
                            switches_data = await response.json()
                            self.log_test("Admin switches", True, f"Total: {switches_data['total_switches']}")
                        else:
                            self.log_test("Admin switches", False, f"Status: {response.status}")
                            
                    # Test system status
                    async with self.session.get(
                        f"{self.base_url}/api/v1/admin/dashboard/status",
                        headers=headers
                    ) as response:
                        
                        if response.status == 200:
                            status_data = await response.json()
                            self.log_test("Admin status", True, f"Status: {status_data['system_status']['server_status']}")
                        else:
                            self.log_test("Admin status", False, f"Status: {response.status}")
                            
                else:
                    error_text = await response.text()
                    self.log_test("Admin config", False, f"Status: {response.status}")
                    
        except Exception as e:
            self.log_test("Admin dashboard", False, str(e))
            
    async def test_user_dashboard(self):
        """Test user dashboard functionality."""
        print("\n👤 TESTING USER DASHBOARD")
        print("=" * 40)
        
        if not self.user_token:
            self.log_test("User dashboard", False, "No user token available")
            return
            
        try:
            headers = {"Authorization": f"Bearer {self.user_token}"}
            
            # Test user dashboard view
            async with self.session.get(
                f"{self.base_url}/api/v1/user/dashboard/view",
                headers=headers
            ) as response:
                
                if response.status == 200:
                    view_data = await response.json()
                    self.log_test("User dashboard view", True, f"Switches: {len(view_data['switches'])}")
                    
                    # Test features endpoint
                    async with self.session.get(
                        f"{self.base_url}/api/v1/user/dashboard/features",
                        headers=headers
                    ) as response:
                        
                        if response.status == 200:
                            features_data = await response.json()
                            self.log_test("User features", True, f"Available: {features_data['total_available']}")
                        else:
                            self.log_test("User features", False, f"Status: {response.status}")
                            
                    # Test system status
                    async with self.session.get(
                        f"{self.base_url}/api/v1/user/dashboard/system-status",
                        headers=headers
                    ) as response:
                        
                        if response.status == 200:
                            status_data = await response.json()
                            self.log_test("User system status", True, f"Status: {status_data['server_status']}")
                        else:
                            self.log_test("User system status", False, f"Status: {response.status}")
                            
                else:
                    error_text = await response.text()
                    self.log_test("User dashboard view", False, f"Status: {response.status}")
                    
        except Exception as e:
            self.log_test("User dashboard", False, str(e))
            
    async def test_switch_controls(self):
        """Test admin switch controls."""
        print("\n🎛️ TESTING SWITCH CONTROLS")
        print("=" * 40)
        
        if not self.admin_token:
            self.log_test("Switch controls", False, "No admin token available")
            return
            
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            
            # Test toggling a switch
            print("🔄 Testing switch toggle...")
            
            # Get current state of AI execution switch
            async with self.session.get(
                f"{self.base_url}/api/v1/admin/dashboard/switches",
                headers=headers
            ) as response:
                
                if response.status == 200:
                    switches_data = await response.json.json()
                    
                    # Find AI execution switch
                    ai_switch = None
                    for switch in switches_data["switches"]:
                        if switch["name"] == "ai_execution_enabled":
                            ai_switch = switch
                            break
                    
                    if ai_switch:
                        original_state = ai_switch["enabled"]
                        new_state = not original_state
                        
                        # Toggle the switch
                        async with self.session.put(
                            f"{self.base_url}/api/v1/admin/dashboard/switches/ai_execution_enabled",
                            json={"enabled": new_state},
                            headers=headers
                        ) as response:
                            
                            if response.status == 200:
                                toggle_result = await response.json()
                                self.log_test("Switch toggle", True, 
                                            f"AI execution: {original_state} → {new_state}")
                                
                                # Toggle back to original state
                                async with self.session.put(
                                    f"{self.base_url}/api/v1/admin/dashboard/switches/ai_execution_enabled",
                                    json={"enabled": original_state},
                                    headers=headers
                                ) as response2:
                                    
                                    if response2.status == 200:
                                        self.log_test("Switch restore", True, 
                                                    f"AI execution: {new_state} → {original_state}")
                                    else:
                                        self.log_test("Switch restore", False, "Failed to restore")
                            else:
                                error_text = await response.text()
                                self.log_test("Switch toggle", False, f"Status: {response.status}")
                    else:
                        self.log_test("Switch toggle", False, "AI execution switch not found")
                        
                else:
                    error_text = await response.text()
                    self.log_test("Switch controls", False, f"Status: {response.status}")
                    
        except Exception as e:
            self.log_test("Switch controls", False, str(e))
            
    async def test_bulk_operations(self):
        """Test bulk operations."""
        print("\n⚡ TESTING BULK OPERATIONS")
        print("=" * 40)
        
        if not self.admin_token:
            self.log_test("Bulk operations", False, "No admin token available")
            return
            
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            
            # Test bulk update
            print("🔄 Testing bulk update...")
            
            bulk_update = {
                "ai_execution_enabled": False,
                "stripe_billing_enabled": True,
                "authentication_required": True
            }
            
            async with self.session.post(
                f"{self.base_url}/api/v1/admin/dashboard/switches/bulk-update",
                json=bulk_update,
                headers=headers
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    self.log_test("Bulk update", True, 
                                f"Updated: {result['total_updated']} switches")
                    
                    # Restore original state
                    restore_update = {
                        "ai_execution_enabled": True,
                        "stripe_billing_enabled": True,
                        "authentication_required": True
                    }
                    
                    async with self.session.post(
                        f"{self.base_url}/api/v1/admin/dashboard/switches/bulk-update",
                        json=restore_update,
                        headers=headers
                    ) as response2:
                        
                        if response2.status == 200:
                            restore_result = await response2.json()
                            self.log_test("Bulk restore", True, 
                                        f"Restored: {restore_result['total_updated']} switches")
                        else:
                            self.log_test("Bulk restore", False, "Failed to restore")
                else:
                    error_text = await response.text()
                    self.log_test("Bulk update", False, f"Status: {response.status}")
                    
        except Exception as e:
            self.log_test("Bulk operations", False, str(e))
            
    async def run_all_tests(self):
        """Run all dashboard tests."""
        print("🚀 DASHBOARD SYSTEM TEST SUITE")
        print("=" * 60)
        print(f"Testing: {self.base_url}")
        print(f"Started: {datetime.now().isoformat()}")
        
        await self.setup()
        
        try:
            await self.test_authentication()
            await self.test_admin_dashboard()
            await self.test_user_dashboard()
            await self.test_switch_controls()
            await self.test_bulk_operations()
            
        finally:
            await self.cleanup()
            
        await self.print_summary()
        
    async def print_summary(self):
        """Print test summary."""
        print("\n" + "=" * 60)
        print("📊 DASHBOARD TEST SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for result in self.test_results if "PASS" in result["status"])
        total = len(self.test_results)
        
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Success Rate: {(passed/total)*100:.1f}%")
        
        if total - passed > 0:
            print("\n❌ FAILED TESTS:")
            for result in self.test_results:
                if "FAIL" in result["status"]:
                    print(f"  - {result['test']}: {result['details']}")
                    
        print(f"\n🎯 DASHBOARD STATUS: {'✅ READY' if passed == total else '⚠️  NEEDS ATTENTION'}")
        print(f"Completed: {datetime.now().isoformat()}")
        
        print(f"\n🌐 ACCESS DASHBOARDS:")
        print(f"  🔧 Admin: {self.base_url}/admin_dashboard.html")
        print(f"  👤 User: {self.base_url}/user_dashboard.html")
        print(f"  🔐 Login: {self.base_url}/api/v1/auth/login")

async def main():
    """Main test runner."""
    tester = DashboardTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())
