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

# Try using pip.exe directly
pip_exe = os.path.join(scripts_path, "pip.exe")

# Add the site-packages to Python path
site_packages = r"C:\Python311\Lib\site-packages"
sys.path.insert(0, site_packages)

# Install required packages directly
required_packages = [
    "fastapi>=0.104.0",
    "uvicorn[standard]>=0.24.0",
    "sqlalchemy>=2.0.0",
    "alembic>=1.12.0",
    "psycopg2-binary>=2.9.0",
    "redis>=5.0.0",
    "pydantic>=2.5.0",
    "pydantic-settings>=2.1.0",
    "python-jose[cryptography]>=3.3.0",
    "passlib[bcrypt]>=1.7.4",
    "python-multipart>=0.0.6",
    "boto3>=1.29.0",
    "httpx>=0.25.0",
    "celery>=5.3.0",
    "python-dotenv>=1.0.0",
    "tiktoken>=0.5.0",
    "cryptography>=41.0.0",
    "prometheus-client>=0.19.0",
    "stripe>=7.0.0"
]

print("Installing required packages...")
for package in required_packages:
    try:
        import pip
        pip.main(['install', package])
    except ImportError:
        subprocess.check_call([pip_exe, "install", package], env=env)
    print(f"Installed {package}")

print("Starting FastAPI server...")
try:
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
except ImportError:
    subprocess.check_call([sys.executable, "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"], env=env)
