@echo off
REM BYOS Command Center - Local Testing Setup for Windows
echo 🎛️  BYOS Command Center - Local Testing Setup
echo ==================================================
echo.
echo This script will set up and run the BYOS system locally for testing.
echo.
echo URLs after setup:
echo - Backend API: http://localhost:8765
echo - Dashboard: http://localhost:4321
echo - API Docs: http://localhost:8765/docs
echo.
echo Press any key to continue...
pause > nul

REM Check if Python is available
python --version > nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python is not installed or not in PATH.
    echo Please install Python 3.8+ and make sure it's in your PATH.
    pause
    exit /b 1
)

REM Check if Node.js is available
node --version > nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Node.js is not installed or not in PATH.
    echo Please install Node.js 16+ and make sure it's in your PATH.
    pause
    exit /b 1
)

echo ✅ Prerequisites check passed
echo.

REM Install Python dependencies
echo 📦 Installing Python dependencies...
pip install fastapi uvicorn sqlalchemy alembic psycopg2-binary python-multipart python-jose[cryptography] passlib[bcrypt] python-dotenv

if %errorlevel% neq 0 (
    echo ❌ Failed to install Python dependencies
    pause
    exit /b 1
)

echo ✅ Python dependencies installed
echo.

REM Install dashboard dependencies
echo 📦 Installing dashboard dependencies...
cd apps\dashboard
if not exist node_modules (
    npm install
    if %errorlevel% neq 0 (
        echo ❌ Failed to install dashboard dependencies
        cd ..\..
        pause
        exit /b 1
    )
) else (
    echo 📦 Dashboard dependencies already installed
)
cd ..\..

echo ✅ Dashboard dependencies installed
echo.

REM Run database migrations
echo 🗄️  Setting up database...
python -c "
import sys
sys.path.append('.')
from alembic.config import Config
from alembic import command
import os
os.environ['ENVIRONMENT'] = 'local_test'
alembic_cfg = Config('alembic/alembic_dev.ini')
command.upgrade(alembic_cfg, 'head')
"
if %errorlevel% neq 0 (
    echo ❌ Database setup failed
    pause
    exit /b 1
)

echo ✅ Database setup complete
echo.

REM Start backend
echo 🚀 Starting BYOS Backend...
start "BYOS Backend" cmd /c "python run_local_test.py"

REM Wait for backend to start
echo ⏳ Waiting for backend to start...
timeout /t 5 /nobreak > nul

REM Start dashboard
echo 🎨 Starting Dashboard...
cd apps\dashboard
start "BYOS Dashboard" cmd /c "npm start"
cd ..\..

echo.
echo 🎉 BYOS Command Center is now running!
echo.
echo Access URLs:
echo - Backend API: http://localhost:8765
echo - Dashboard: http://localhost:4321
echo - API Docs: http://localhost:8765/docs
echo.
echo Press any key to exit (this won't stop the services)...
pause > nul
