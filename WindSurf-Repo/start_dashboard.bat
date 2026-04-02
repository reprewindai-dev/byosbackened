@echo off
REM Simple BYOS Dashboard Startup Script
echo Starting BYOS Dashboard on port 4321...
echo Press Ctrl+C to stop
echo.

REM Go to dashboard directory
cd apps\dashboard

REM Start the dashboard
npm start
