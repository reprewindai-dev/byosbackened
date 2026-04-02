@echo off
echo 🎛️  BYOS Command Center - Local Testing Setup
echo ==================================================
echo.
echo Backend will run on: http://localhost:8765
echo Dashboard will run on: http://localhost:4321
echo.
echo Press Ctrl+C to stop both services
echo.

REM Start backend in background
start "BYOS Backend" cmd /c "cd /d %~dp0 && python run_local_test.py"

REM Wait a moment for backend to start
timeout /t 3 /nobreak > nul

REM Start dashboard
cd apps\dashboard
npm start
