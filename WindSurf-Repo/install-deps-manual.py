#!/usr/bin/env python
import subprocess
import sys
import os

# Ensure pip is available
sys.path.insert(0, r"C:\Python311\Scripts")
try:
    import pip
except ImportError:
    subprocess.check_call([sys.executable, "bootstrap-pip.py"])
    import pip

# Install dependencies
subprocess.check_call([sys.executable, "-m", "pip", "install", "-e", "."])
