@echo off
REM BYOS System Diagnostic Script
echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║                    BYOS SYSTEM DIAGNOSTIC                   ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.
echo Checking your BYOS Command Center setup...
echo.

echo 🔍 Checking Python installation...
python --version
if %errorlevel% neq 0 (
    echo ❌ Python not found!
    echo Please install Python 3.8+ from https://python.org
    echo Make sure to check "Add Python to PATH" during installation.
    goto :error
)
echo ✅ Python found
echo.

echo 🔍 Checking Node.js installation...
node --version
if %errorlevel% neq 0 (
    echo ❌ Node.js not found!
    echo Please install Node.js 16+ from https://nodejs.org
    goto :error
)
echo ✅ Node.js found
echo.

echo 🔍 Checking npm...
npm --version
if %errorlevel% neq 0 (
    echo ❌ npm not found!
    goto :error
)
echo ✅ npm found
echo.

echo 📦 Checking Python dependencies...
python -c "import fastapi; print('✅ FastAPI found')" 2>nul
if %errorlevel% neq 0 (
    echo ❌ FastAPI not installed
    goto :error
)

python -c "import uvicorn; print('✅ Uvicorn found')" 2>nul
if %errorlevel% neq 0 (
    echo ❌ Uvicorn not installed
    goto :error
)

python -c "import sqlalchemy; print('✅ SQLAlchemy found')" 2>nul
if %errorlevel% neq 0 (
    echo ❌ SQLAlchemy not installed
    goto :error
)
echo ✅ Python dependencies found
echo.

echo 📦 Checking dashboard dependencies...
if exist apps\dashboard\node_modules (
    echo ✅ Dashboard dependencies found
) else (
    echo ❌ Dashboard dependencies not found
    echo Run: cd apps\dashboard && npm install
    goto :error
)
echo.

echo 🗄️ Checking database setup...
if exist test_byos.db (
    echo ✅ Database file exists
) else (
    echo ⚠️ Database file not found (will be created on first run)
)
echo.

echo 🌐 Checking port availability...
netstat -an | find "4321" >nul
if %errorlevel% equ 0 (
    echo ⚠️ Port 4321 (dashboard) is already in use!
) else (
    echo ✅ Port 4321 (dashboard) is available
)

netstat -an | find "8765" >nul
if %errorlevel% equ 0 (
    echo ⚠️ Port 8765 (backend) is already in use!
) else (
    echo ✅ Port 8765 (backend) is available
)
echo.

echo 🚀 System diagnostic complete!
echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║                    STARTUP INSTRUCTIONS                     ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.
echo 1. Start Backend: Double-click 'start_backend.bat'
echo 2. Start Dashboard: Double-click 'start_dashboard.bat'
echo.
echo Or run both manually:
echo Backend: python run_local_test.py
echo Dashboard: cd apps\dashboard && npm start
echo.
echo URLs:
echo Dashboard: http://localhost:4321
echo Backend: http://localhost:8765
echo API Docs: http://localhost:8765/docs
echo.
goto :end

:error
echo.
echo ❌ Diagnostic found issues. Please fix them and run this script again.
echo.
pause
exit /b 1

:end
echo Press any key to close...
pause > nul
