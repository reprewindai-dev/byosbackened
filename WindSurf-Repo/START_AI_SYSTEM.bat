@echo off
echo ========================================
echo AI EXECUTION SYSTEM STARTUP
echo ========================================
echo.

echo Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo Python not found in PATH!
    echo.
    echo OPTIONS:
    echo 1. Install Python from https://python.org
    echo 2. Add Python to PATH if already installed
    echo 3. Use python3 or py commands instead
    echo.
    echo Trying alternative Python commands...
    echo.
    
    py --version >nul 2>&1
    if errorlevel 1 (
        python3 --version >nul 2>&1
        if errorlevel 1 (
            echo ❌ No Python installation found!
            echo Please install Python and try again.
            echo.
            echo Download: https://python.org/downloads/
            pause
            exit /b 1
        ) else (
            echo ✅ Found python3
            set PYTHON_CMD=python3
        )
    ) else (
        echo ✅ Found py launcher
        set PYTHON_CMD=py
    )
) else (
    echo ✅ Found python in PATH
    set PYTHON_CMD=python
)

echo.
echo Installing dependencies...
%PYTHON_CMD% -m pip install -r requirements.txt
if errorlevel 1 (
    echo ⚠️  Some dependencies may have failed to install
    echo Continuing anyway...
)

echo.
echo Testing imports...
%PYTHON_CMD% test_imports.py
if errorlevel 1 (
    echo ❌ Import test failed!
    echo Please check the error messages above.
    pause
    exit /b 1
)

echo.
echo Starting AI Execution System Server...
echo Server will be available at: http://localhost:8000
echo API docs at: http://localhost:8000/api/v1/docs
echo.
echo Press Ctrl+C to stop the server
echo.

%PYTHON_CMD% -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

echo.
echo Server stopped.
pause
