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

subprocess.check_call([sys.executable, "-m", "pip", "install", "-e", "."], env=env)
