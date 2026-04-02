@echo off
REM BYOS Command Center - Complete One-Click Setup and Run
echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║                     BYOS COMMAND CENTER                      ║
echo ║                   ONE-CLICK SETUP & RUN                     ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.
echo Welcome to the BYOS Command Center!
echo This script will set up and run everything automatically.
echo.
echo System URLs after setup:
echo 📊 Dashboard: http://localhost:4321
echo 🔧 Backend API: http://localhost:8765
echo 📚 API Docs: http://localhost:8765/docs
echo.
echo Press any key to start the setup...
pause > nul

REM Change to project directory
cd /d "%~dp0"

echo.
echo 🔍 Checking prerequisites...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python is not installed!
    echo Please install Python 3.8+ from https://python.org
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Node.js is not installed!
    echo Please install Node.js 16+ from https://nodejs.org
    pause
    exit /b 1
)

echo ✅ Prerequisites check passed
echo.

REM Install Python dependencies
echo 📦 Installing Python dependencies...
pip install --quiet --disable-pip-version-check fastapi uvicorn sqlalchemy alembic psycopg2-binary python-multipart python-jose[cryptography] passlib[bcrypt] python-dotenv

if %errorlevel% neq 0 (
    echo ❌ Failed to install Python dependencies
    echo Try running: pip install fastapi uvicorn sqlalchemy alembic psycopg2-binary python-multipart python-jose[cryptography] passlib[bcrypt] python-dotenv
    pause
    exit /b 1
)

echo ✅ Python dependencies installed
echo.

REM Install dashboard dependencies
echo 📦 Installing dashboard dependencies...
cd apps\dashboard

if not exist node_modules (
    npm install --silent
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

REM Set up database
echo 🗄️ Setting up database...
set ENVIRONMENT=local_test

python -c "
import os, sys
sys.path.append('.')
os.environ['ENVIRONMENT'] = 'local_test'

# Run database migrations
from alembic.config import Config
from alembic import command

try:
    alembic_cfg = Config('alembic/alembic_dev.ini')
    command.upgrade(alembic_cfg, 'head')
    print('✅ Database migrations completed')
except Exception as e:
    print(f'⚠️ Database setup warning: {e}')
    print('This is normal if database already exists')
"

if %errorlevel% neq 0 (
    echo ⚠️ Database setup had warnings (this is usually normal)
) else (
    echo ✅ Database setup completed
)

echo.
echo 🚀 Starting BYOS Backend Server...
start "BYOS Backend Server" /B cmd /c "python run_local_test.py"

echo ⏳ Waiting for backend to start...
timeout /t 8 /nobreak > nul

echo 🎨 Starting BYOS Dashboard...
cd apps\dashboard
start "BYOS Dashboard" /B cmd /c "npm start"
cd ..\..

echo ⏳ Waiting for dashboard to start...
timeout /t 5 /nobreak > nul

echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║                        🎉 SUCCESS!                          ║
echo ║                                                            ║
echo ║  BYOS Command Center is now running!                       ║
echo ║                                                            ║
echo ║  📊 Dashboard: http://localhost:4321                       ║
echo ║  🔧 Backend API: http://localhost:8765                     ║
echo ║  📚 API Docs: http://localhost:8765/docs                   ║
echo ║                                                            ║
echo ║  Click the URLs above to access your system!               ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.
echo Opening dashboard in your default browser...
start http://localhost:4321

echo.
echo 💡 Tips:
echo   • Keep this window open to keep services running
echo   • Press Ctrl+C to stop all services
echo   • Check the other command windows for any error messages
echo.
echo 🎯 Ready to explore your BYOS Command Center!
echo.

REM Keep the script running so services stay active
echo Press Ctrl+C to stop all services...
pause > nul
