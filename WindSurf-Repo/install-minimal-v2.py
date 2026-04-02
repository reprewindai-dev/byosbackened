#!/usr/bin/env python
import subprocess
import sys
import os

# Add Scripts to PATH
scripts_path = r"C:\Python311\Scripts"
os.environ["PATH"] = scripts_path + os.pathsep + os.environ.get("PATH", "")

# Add site-packages to Python path
site_packages = r"C:\Python311\Lib\site-packages"
sys.path.insert(0, site_packages)

# Install minimal dependencies
def install_deps():
    pip_exe = os.path.join(scripts_path, "pip.exe")
    packages = ["fastapi", "uvicorn", "pydantic"]
    
    for package in packages:
        print(f"Installing {package}...")
        try:
            # Try using pip module
            import pip
            pip.main(['install', package])
        except ImportError:
            # Try using pip.exe directly
            env = os.environ.copy()
            env["PATH"] = scripts_path + os.pathsep + env.get("PATH", "")
            subprocess.check_call([pip_exe, "install", package], env=env)
        print(f"Installed {package}")

if __name__ == "__main__":
    install_deps()
    print("Dependencies installed. Run: python minimal-server.py")
