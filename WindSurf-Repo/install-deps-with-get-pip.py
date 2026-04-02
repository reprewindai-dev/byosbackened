#!/usr/bin/env python
import subprocess
import sys
import os
import urllib.request
import tempfile

# Download get-pip.py
GET_PIP_URL = "https://bootstrap.pypa.io/get-pip.py"
with tempfile.NamedTemporaryFile(delete=False, mode="wb") as f:
    urllib.request.urlretrieve(GET_PIP_URL, f.name)
    pip_installer = f.name

# Run get-pip.py
subprocess.check_call([sys.executable, pip_installer])
os.unlink(pip_installer)

# Add Scripts to PATH
scripts_path = r"C:\Python311\Scripts"
os.environ["PATH"] = scripts_path + os.pathsep + os.environ.get("PATH", "")

# Install dependencies
subprocess.check_call([sys.executable, "-m", "pip", "install", "-e", "."])
