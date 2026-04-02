#!/usr/bin/env python3
"""
DEPENDENCY VALIDATOR
===================

Checks if all dependencies are installed for the full app test.
"""

import sys
import subprocess
import importlib.util

def check_python_package(package_name: str, import_name: str = None) -> bool:
    """Check if a Python package is installed."""
    try:
        import_name = import_name or package_name
        spec = importlib.util.find_spec(import_name)
        return spec is not None
    except ImportError:
        return False

def check_command(command: str) -> bool:
    """Check if a command is available."""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        return result.returncode == 0
    except:
        return False

def validate_dependencies():
    """Validate all required dependencies."""
    
    print("🔍 VALIDATING DEPENDENCIES")
    print("=" * 40)
    
    required_packages = [
        ("fastapi", "fastapi"),
        ("uvicorn", "uvicorn"),
        ("sqlalchemy", "sqlalchemy"),
        ("pydantic", "pydantic"),
        ("stripe", "stripe"),
        ("aiohttp", "aiohttp"),
        ("python-dotenv", "dotenv"),
    ]
    
    missing_packages = []
    
    print("📦 Python Packages:")
    for package, import_name in required_packages:
        if check_python_package(package, import_name):
            print(f"  ✅ {package}")
        else:
            print(f"  ❌ {package} - MISSING")
            missing_packages.append(package)
    
    print("\n🔧 Commands:")
    commands = [
        ("curl", "curl --version"),
        ("python", "python --version"),
    ]
    
    for command, version_cmd in commands:
        if check_command(version_cmd):
            print(f"  ✅ {command}")
        else:
            print(f"  ❌ {command} - MISSING")
    
    print("\n📁 Configuration Files:")
    config_files = [
        ".env",
        "requirements.txt",
        "api/main.py",
        "core/governance/pipeline.py",
        "core/revenue/billing_stripe.py",
    ]
    
    import os
    for file_path in config_files:
        if os.path.exists(file_path):
            print(f"  ✅ {file_path}")
        else:
            print(f"  ❌ {file_path} - MISSING")
    
    if missing_packages:
        print(f"\n📦 INSTALLING MISSING PACKAGES...")
        install_cmd = f"pip install {' '.join(missing_packages)}"
        print(f"Running: {install_cmd}")
        
        try:
            result = subprocess.run(install_cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                print("✅ Packages installed successfully")
                return True
            else:
                print(f"❌ Installation failed: {result.stderr}")
                return False
        except Exception as e:
            print(f"❌ Installation error: {e}")
            return False
    else:
        print("\n✅ ALL DEPENDENCIES SATISFIED")
        return True

def show_next_steps():
    """Show next steps for testing."""
    
    print("\n🚀 READY TO TEST!")
    print("=" * 40)
    print("Run: TEST_EVERYTHING.bat")
    print("Or: python test_full_app.py")
    print("\nThis will test:")
    print("  🤖 AI execution system")
    print("  💳 Stripe billing")
    print("  🌐 All API endpoints")
    print("  🗄️  Database connectivity")
    print("  🔌 Provider system")
    print("  🏥 Health endpoints")

if __name__ == "__main__":
    success = validate_dependencies()
    
    if success:
        show_next_steps()
        sys.exit(0)
    else:
        print("\n❌ DEPENDENCY VALIDATION FAILED")
        print("Please install missing dependencies and try again")
        sys.exit(1)
