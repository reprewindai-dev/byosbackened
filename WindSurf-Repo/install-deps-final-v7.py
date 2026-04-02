#!/usr/bin/env python
import subprocess
import sys
import os

# Ensure Scripts is on PATH for this process
scripts_path = r"C:\Python311\Scripts"
os.environ["PATH"] = scripts_path + os.pathsep + os.environ.get("PATH", "")

# Use the pip script directly via subprocess with proper PATH
env = os.environ.copy()
env["PATH"] = scripts_path + os.pathsep + env.get("PATH", "")

# Try using pip.exe directly
pip_exe = os.path.join(scripts_path, "pip.exe")

# Add the site-packages to Python path
site_packages = r"C:\Python311\Lib\site-packages"
sys.path.insert(0, site_packages)

# Install setuptools first
try:
    import pip
    pip.main(['install', '--upgrade', 'setuptools', 'wheel'])
except ImportError:
    subprocess.check_call([pip_exe, "install", "--upgrade", "setuptools", "wheel"], env=env)

# Now install the project
try:
    pip.main(['install', '-e', '.'])
except ImportError:
    subprocess.check_call([pip_exe, "install", "-e", "."], env=env)
