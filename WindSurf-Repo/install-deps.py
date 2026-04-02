#!/usr/bin/env python
import subprocess
import sys
import os

# Add Scripts to PATH
scripts_path = r"C:\Python311\Scripts"
os.environ["PATH"] = scripts_path + os.pathsep + os.environ.get("PATH", "")

# Install dependencies
subprocess.check_call([sys.executable, "-m", "pip", "install", "-e", "."])
