#!/usr/bin/env python
import os
import sys
import urllib.request
import subprocess
import tempfile

# Download get-pip.py
GET_PIP_URL = "https://bootstrap.pypa.io/get-pip.py"
with tempfile.NamedTemporaryFile(delete=False, mode="wb") as f:
    urllib.request.urlretrieve(GET_PIP_URL, f.name)
    pip_installer = f.name

# Run get-pip.py
subprocess.check_call([sys.executable, pip_installer])
os.unlink(pip_installer)
