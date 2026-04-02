#!/usr/bin/env python
import subprocess
import sys
import os

# Ensure Scripts is on PATH for this process
scripts_path = r"C:\Python311\Scripts"
os.environ["PATH"] = scripts_path + os.pathsep + os.environ.get("PATH", "")

# Directly invoke pip module
subprocess.check_call([sys.executable, "-c", "import pip; pip.main(['install', '-e', '.'])"])
