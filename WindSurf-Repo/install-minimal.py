#!/usr/bin/env python
import subprocess
import sys
import os
import urllib.request
import tempfile

# Download and install pip if not available
def ensure_pip():
    try:
        import pip
        return True
    except ImportError:
        print("Installing pip...")
        GET_PIP_URL = "https://bootstrap.pypa.io/get-pip.py"
        with tempfile.NamedTemporaryFile(delete=False, mode="wb") as f:
            urllib.request.urlretrieve(GET_PIP_URL, f.name)
            pip_installer = f.name
        
        subprocess.check_call([sys.executable, pip_installer])
        os.unlink(pip_installer)
        
        # Add Scripts to PATH
        scripts_path = r"C:\Python311\Scripts"
        os.environ["PATH"] = scripts_path + os.pathsep + os.environ.get("PATH", "")
        
        # Try importing pip again
        try:
            import pip
            return True
        except ImportError:
            return False

# Install minimal dependencies
def install_deps():
    scripts_path = r"C:\Python311\Scripts"
    pip_exe = os.path.join(scripts_path, "pip.exe")
    
    packages = ["fastapi", "uvicorn", "pydantic"]
    
    for package in packages:
        print(f"Installing {package}...")
        try:
            import pip
            pip.main(['install', package])
        except ImportError:
            # Try using pip.exe directly
            env = os.environ.copy()
            env["PATH"] = scripts_path + os.pathsep + env.get("PATH", "")
            subprocess.check_call([pip_exe, "install", package], env=env)
        print(f"Installed {package}")

if __name__ == "__main__":
    if ensure_pip():
        print("Pip is available")
        install_deps()
        print("Dependencies installed. Run: python minimal-server.py")
    else:
        print("Failed to install pip")
        sys.exit(1)
