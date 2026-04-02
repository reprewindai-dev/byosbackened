"""
Production Test Suite Runner
============================

Comprehensive test execution script for BYOS AI Backend production validation.
"""

import pytest
import sys
import os
import asyncio
import subprocess
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

class TestRunner:
    """Production test runner with comprehensive test coverage."""
    
    def __init__(self):
        self.test_results = {}
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        
    def run_unit_tests(self):
        """Run unit tests."""
        print("🧪 Running Unit Tests...")
        
        test_files = [
            "tests/test_auth.py",
            "tests/test_workspaces.py", 
            "tests/test_ai_execution.py",
            "tests/test_billing.py",
            "tests/test_dashboard.py"
        ]
        
        for test_file in test_files:
            if Path(test_file).exists():
                result = self._run_pytest([test_file, "-v", "--tb=short"])
                self.test_results[f"unit_{test_file}"] = result
            else:
                print(f"⚠️  Test file not found: {test_file}")
    
    def run_integration_tests(self):
        """Run integration tests."""
        print("🔗 Running Integration Tests...")
        
        result = self._run_pytest([
            "tests/test_integration.py",
            "-v", 
            "--tb=short",
            "-m", "integration"
        ])
        
        self.test_results["integration"] = result
    
    def run_load_tests(self):
        """Run load tests."""
        print("⚡ Running Load Tests...")
        
        result = self._run_pytest([
            "tests/test_load.py",
            "-v",
            "--tb=short", 
            "-m", "load"
        ])
        
        self.test_results["load"] = result
    
    def run_performance_tests(self):
        """Run performance tests."""
        print("📊 Running Performance Tests...")
        
        result = self._run_pytest([
            "tests/test_performance.py",
            "-v",
            "--tb=short",
            "-m", "performance"
        ])
        
        self.test_results["performance"] = result
    
    def run_api_tests(self):
        """Run API endpoint tests."""
        print("🌐 Running API Tests...")
        
        result = self._run_pytest([
            "tests/test_api_endpoints.py",
            "-v",
            "--tb=short"
        ])
        
        self.test_results["api"] = result
    
    def run_security_tests(self):
        """Run security tests."""
        print("🔒 Running Security Tests...")
        
        result = self._run_pytest([
            "tests/test_security.py",
            "-v",
            "--tb=short"
        ])
        
        self.test_results["security"] = result
    
    def run_database_tests(self):
        """Run database tests."""
        print("🗄️  Running Database Tests...")
        
        result = self._run_pytest([
            "tests/test_database.py",
            "-v",
            "--tb=short"
        ])
        
        self.test_results["database"] = result
    
    def run_cache_tests(self):
        """Run cache tests."""
        print("💾 Running Cache Tests...")
        
        result = self._run_pytest([
            "tests/test_cache.py",
            "-v",
            "--tb=short"
        ])
        
        self.test_results["cache"] = result
    
    def _run_pytest(self, args):
        """Run pytest with given arguments."""
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pytest"] + args,
                capture_output=True,
                text=True,
                cwd=project_root
            )
            
            # Parse results
            output = result.stdout + result.stderr
            passed = result.returncode == 0
            
            return {
                "passed": passed,
                "output": output,
                "return_code": result.returncode
            }
            
        except Exception as e:
            return {
                "passed": False,
                "output": str(e),
                "return_code": 1
            }
    
    def generate_report(self):
        """Generate comprehensive test report."""
        print("\n" + "="*80)
        print("📋 COMPREHENSIVE TEST REPORT")
        print("="*80)
        
        total_suites = len(self.test_results)
        passed_suites = sum(1 for result in self.test_results.values() if result["passed"])
        
        print(f"Test Suites: {passed_suites}/{total_suites} passed")
        print(f"Overall Status: {'✅ PASSED' if passed_suites == total_suites else '❌ FAILED'}")
        
        print("\n" + "-"*60)
        print("DETAILED RESULTS:")
        print("-"*60)
        
        for suite_name, result in self.test_results.items():
            status = "✅ PASSED" if result["passed"] else "❌ FAILED"
            print(f"{suite_name}: {status}")
            
            if not result["passed"]:
                print(f"  Error: {result['output'][:200]}...")
        
        print("\n" + "="*80)
        
        return passed_suites == total_suites
    
    def run_all_tests(self):
        """Run complete test suite."""
        print("🚀 Starting Comprehensive Test Suite...")
        print(f"Working Directory: {project_root}")
        
        # Check if server is running
        if not self._check_server():
            print("❌ Server is not running. Please start the server first.")
            return False
        
        # Run all test categories
        test_methods = [
            self.run_unit_tests,
            self.run_integration_tests,
            self.run_api_tests,
            self.run_database_tests,
            self.run_cache_tests,
            self.run_security_tests,
            self.run_performance_tests,
            self.run_load_tests
        ]
        
        for test_method in test_methods:
            try:
                test_method()
            except Exception as e:
                print(f"❌ Test suite failed: {e}")
        
        # Generate report
        return self.generate_report()
    
    def _check_server(self):
        """Check if server is running."""
        try:
            import requests
            response = requests.get("http://localhost:8000/health", timeout=5)
            return response.status_code == 200
        except:
            return False

def main():
    """Main test runner."""
    runner = TestRunner()
    success = runner.run_all_tests()
    
    if success:
        print("\n🎉 ALL TESTS PASSED - SYSTEM READY FOR PRODUCTION!")
        return 0
    else:
        print("\n❌ SOME TESTS FAILED - REVIEW AND FIX ISSUES")
        return 1

if __name__ == "__main__":
    sys.exit(main())
