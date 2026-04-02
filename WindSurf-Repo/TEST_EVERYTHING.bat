@echo off
echo ========================================
echo BYOS AI BACKEND - COMPREHENSIVE TEST
echo ========================================
echo.

echo 🔍 CHECKING SYSTEM STATUS...
echo.

REM Check if server is running
curl -s http://localhost:8000/health >nul 2>&1
if errorlevel 1 (
    echo ❌ Server not running at http://localhost:8000
    echo.
    echo 🚀 STARTING SERVER...
    echo.
    
    REM Try to start the server
    echo Starting AI Execution System with all features...
    echo Server will be available at: http://localhost:8000
    echo API docs at: http://localhost:8000/api/v1/docs
    echo.
    echo Features:
    echo ✅ Complete AI execution system
    echo ✅ Sovereign governance pipeline  
    echo ✅ Stripe billing integration
    echo ✅ All API endpoints
    echo ✅ Database connectivity
    echo ✅ Provider system
    echo.
    echo Press Ctrl+C to stop the server
    echo.
    
    REM Start server in background and then test
    start /B python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
    
    echo Waiting for server to start...
    timeout /t 10 /nobreak >nul
    
    REM Check if server started
    curl -s http://localhost:8000/health >nul 2>&1
    if errorlevel 1 (
        echo ❌ Server failed to start
        echo.
        echo Please check:
        echo 1. Python installation
        echo 2. Dependencies: pip install -r requirements.txt
        echo 3. Environment variables in .env file
        echo.
        pause
        exit /b 1
    ) else (
        echo ✅ Server started successfully!
    )
) else (
    echo ✅ Server is already running
)

echo.
echo 🧪 RUNNING COMPREHENSIVE TESTS...
echo.

REM Run the comprehensive test
python test_full_app.py --url http://localhost:8000

echo.
echo ========================================
echo TEST COMPLETE
echo ========================================
echo.
echo 📊 Check the results above to see system status
echo.
echo 🌐 Available endpoints:
echo   http://localhost:8000/api/v1/docs - API Documentation
echo   http://localhost:8000/api/v1/governance/execute - AI Execution
echo   http://localhost:8000/api/v1/stripe/plans - Billing Plans
echo.
echo 💡 To test manually:
echo   curl -X POST http://localhost:8000/api/v1/governance/execute ^
echo        -H "Content-Type: application/json" ^
echo        -d "{\"operation_type\":\"summarize\",\"input_text\":\"Test text\",\"temperature\":0.7,\"max_tokens\":256}"
echo.

pause
