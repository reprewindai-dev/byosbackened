@echo off
echo ========================================
echo AI EXECUTION SYSTEM API TEST
echo ========================================
echo.

echo Testing AI execution endpoint...
echo.

REM Test health endpoint first
echo Testing health endpoint...
curl -s http://localhost:8000/health
if errorlevel 1 (
    echo ❌ Server not responding at http://localhost:8000
    echo Please start the server first with START_AI_SYSTEM.bat
    pause
    exit /b 1
)

echo.
echo ✅ Server is running!
echo.

REM Test governance execute endpoint
echo Testing governance execute endpoint...
curl -X POST http://localhost:8000/api/v1/governance/execute ^
-H "Content-Type: application/json" ^
-d "{\"operation_type\":\"summarize\",\"input_text\":\"This is a test text for the AI execution system. The sovereign governance pipeline should process this request and return a governed summary that meets all quality and compliance requirements.\",\"temperature\":0.7,\"max_tokens\":256}"

echo.
echo.
echo Test completed!
echo.
echo You can also test manually with:
echo curl -X POST http://localhost:8000/api/v1/governance/execute -H "Content-Type: application/json" -d "{\"operation_type\":\"summarize\",\"input_text\":\"Your text here\",\"temperature\":0.7,\"max_tokens\":256}"
echo.
pause
