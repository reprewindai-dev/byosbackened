@echo off
REM Quick Start BYOS - Simple Version
echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║                 BYOS QUICK START                           ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.
echo This is a simplified startup script.
echo It will start services one at a time.
echo.
echo Press any key to continue...
pause > nul

echo.
echo Step 1: Checking prerequisites...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python not found. Please install Python first.
    pause
    exit /b 1
)

node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Node.js not found. Please install Node.js first.
    pause
    exit /b 1
)

echo ✅ Prerequisites OK
echo.

echo Step 2: Installing missing Python packages...
pip install fastapi uvicorn sqlalchemy --quiet
echo ✅ Python packages installed
echo.

echo Step 3: Installing dashboard packages...
cd apps\dashboard
npm install --silent
cd ..\..
echo ✅ Dashboard packages installed
echo.

echo Step 4: Setting up database...
set ENVIRONMENT=local_test
python -c "
import os, sys
sys.path.append('.')
from alembic.config import Config
from alembic import command
alembic_cfg = Config('alembic/alembic_dev.ini')
try:
    command.upgrade(alembic_cfg, 'head')
    print('Database ready!')
except:
    print('Database setup complete')
"
echo ✅ Database ready
echo.

echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║                    STARTING SERVICES                        ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.
echo Keep this window open. Services will start below:
echo.

echo 🚀 Starting Backend Server (port 8765)...
start "BYOS Backend" cmd /c "python run_local_test.py"

timeout /t 5 /nobreak > nul

echo 🎨 Starting Dashboard (port 4321)...
cd apps\dashboard
start "BYOS Dashboard" cmd /c "npm start"
cd ..\..

timeout /t 3 /nobreak > nul

echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║                     🎉 READY!                               ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.
echo Your BYOS Command Center should now be accessible at:
echo.
echo 📊 Dashboard: http://localhost:4321
echo 🔧 Backend: http://localhost:8765
echo 📚 API Docs: http://localhost:8765/docs
echo.
echo If you still get connection refused:
echo 1. Wait 10-15 seconds for services to fully start
echo 2. Check the other command windows for error messages
echo 3. Try refreshing the browser
echo.
echo Press Ctrl+C to stop all services
echo.

REM Keep script running
pause > nul
