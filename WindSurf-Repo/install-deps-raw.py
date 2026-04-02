#!/usr/bin/env python
import subprocess
import sys
import os

# Add Scripts to sys.path
sys.path.insert(0, r"C:\Python311\Scripts")

# Import pip and run install
import pip
pip.main(['install', '-e', '.'])
