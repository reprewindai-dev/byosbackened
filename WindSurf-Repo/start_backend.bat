@echo off
REM Simple BYOS Backend Startup Script
echo Starting BYOS Backend Server on port 8765...
echo Press Ctrl+C to stop
echo.

REM Set environment
set ENVIRONMENT=local_test
set API_PORT=8765

REM Start the server
python run_local_test.py
