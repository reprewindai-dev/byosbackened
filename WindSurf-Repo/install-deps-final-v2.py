#!/usr/bin/env python
import subprocess
import sys
import os

# Ensure Scripts is on PATH for this process
scripts_path = r"C:\Python311\Scripts"
os.environ["PATH"] = scripts_path + os.pathsep + os.environ.get("PATH", "")

# Use the pip script directly
pip_script = os.path.join(scripts_path, "pip.exe")
subprocess.check_call([sys.executable, pip_script, "install", "-e", "."])
