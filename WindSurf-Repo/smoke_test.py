#!/usr/bin/env python3
"""
SMOKE TEST FOR AI EXECUTION SYSTEM
==================================

This script performs a comprehensive smoke test of the AI execution system
without requiring the server to be running. It validates all critical components.
"""

import os
import sys
import importlib.util

def test_file_exists(filepath, description):
    """Test if a file exists."""
    if os.path.exists(filepath):
        print(f"✅ {description}: {filepath}")
        return True
    else:
        print(f"❌ {description}: {filepath} - NOT FOUND")
        return False

def test_python_import(module_path, description):
    """Test if a Python module can be imported."""
    try:
        spec = importlib.util.spec_from_file_location(module_path, module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        print(f"✅ {description}: {module_path}")
        return True
    except Exception as e:
        print(f"❌ {description}: {module_path} - {str(e)}")
        return False

def run_smoke_test():
    """Run comprehensive smoke test."""
    
    print("🧪 AI EXECUTION SYSTEM SMOKE TEST")
    print("=" * 60)
    
    tests_passed = 0
    total_tests = 0
    
    # Test critical files exist
    critical_files = [
        ("core/governance/__init__.py", "Governance module init"),
        ("core/governance/pipeline.py", "Governance pipeline"),
        ("core/governance/schemas.py", "Governance schemas"),
        ("core/governance/sovereign_helpers.py", "Sovereign helpers"),
        ("core/providers/__init__.py", "Providers init"),
        ("core/providers/registry.py", "Provider registry"),
        ("apps/api/routers/governance.py", "Governance API router"),
        ("api/main.py", "Main API application"),
        ("test_ai_execution.py", "AI execution test script"),
        ("test_api_endpoint.py", "API endpoint test script"),
    ]
    
    print("\n📁 CRITICAL FILES CHECK:")
    for filepath, description in critical_files:
        total_tests += 1
        if test_file_exists(filepath, description):
            tests_passed += 1
    
    # Test Python imports
    print("\n🐍 PYTHON IMPORTS CHECK:")
    python_modules = [
        ("core/governance/__init__.py", "Governance module"),
        ("core/governance/schemas.py", "Governance schemas"),
        ("core/governance/sovereign_helpers.py", "Sovereign helpers"),
    ]
    
    for module_path, description in python_modules:
        total_tests += 1
        if test_python_import(module_path, description):
            tests_passed += 1
    
    # Test directory structure
    print("\n📂 DIRECTORY STRUCTURE CHECK:")
    critical_dirs = [
        ("core/governance", "Governance directory"),
        ("core/providers", "Providers directory"),
        ("apps/api/routers", "API routers directory"),
        ("apps/ai/providers", "AI providers directory"),
    ]
    
    for dirpath, description in critical_dirs:
        total_tests += 1
        if os.path.exists(dirpath) and os.path.isdir(dirpath):
            print(f"✅ {description}: {dirpath}")
            tests_passed += 1
        else:
            print(f"❌ {description}: {dirpath} - NOT FOUND")
    
    # Test configuration files
    print("\n⚙️  CONFIGURATION FILES CHECK:")
    config_files = [
        ("core/config.py", "Core config"),
        ("api/main.py", "API main"),
        ("requirements.txt", "Requirements"),
    ]
    
    for filepath, description in config_files:
        total_tests += 1
        if test_file_exists(filepath, description):
            tests_passed += 1
    
    # Test for specific schema fields
    print("\n🔍 SCHEMA VALIDATION CHECK:")
    try:
        with open("core/governance/schemas.py", "r") as f:
            schema_content = f.read()
            
        schema_fields = [
            "entropy_score",
            "fracture_detected", 
            "governance_tier_boost",
            "assigned_tier",
            "temperature",
            "max_tokens"
        ]
        
        for field in schema_fields:
            total_tests += 1
            if field in schema_content:
                print(f"✅ Schema field '{field}' found")
                tests_passed += 1
            else:
                print(f"❌ Schema field '{field}' missing")
                
    except Exception as e:
        print(f"❌ Schema validation failed: {e}")
        total_tests += len(schema_fields)
    
    # Test for governance router in main API
    print("\n🔗 API INTEGRATION CHECK:")
    try:
        with open("api/main.py", "r") as f:
            main_content = f.read()
            
        if "governance" in main_content:
            print("✅ Governance router imported in main API")
            tests_passed += 1
        else:
            print("❌ Governance router not found in main API")
        total_tests += 1
        
    except Exception as e:
        print(f"❌ API integration check failed: {e}")
        total_tests += 1
    
    # Results summary
    print("\n" + "=" * 60)
    print(f"📊 SMOKE TEST RESULTS:")
    print(f"Tests Passed: {tests_passed}/{total_tests}")
    print(f"Success Rate: {(tests_passed/total_tests)*100:.1f}%")
    
    if tests_passed == total_tests:
        print("🎉 ALL SMOKE TESTS PASSED!")
        print("✅ AI execution system appears to be properly configured")
        return True
    else:
        print("⚠️  SOME SMOKE TESTS FAILED")
        print("❌ There may be configuration issues")
        return False

if __name__ == "__main__":
    success = run_smoke_test()
    sys.exit(0 if success else 1)
