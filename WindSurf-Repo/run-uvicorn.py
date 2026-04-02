#!/usr/bin/env python
import subprocess
import sys
import os

# Add Scripts to PATH
scripts_path = r"C:\Python311\Scripts"
os.environ["PATH"] = scripts_path + os.pathsep + os.environ.get("PATH", "")

# Directly run uvicorn via python -m
subprocess.check_call([sys.executable, "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"])
