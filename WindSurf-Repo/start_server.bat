@echo off
echo Starting AI Execution System Server...
echo.

REM Try different Python commands
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
if errorlevel 1 (
    echo Python command failed, trying py...
    py -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
    if errorlevel 1 (
        echo py command failed, trying python3...
        python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
        if errorlevel 1 (
            echo All Python commands failed. Please check Python installation.
            echo You can manually start the server with:
            echo   python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
            pause
        )
    )
)

pause
