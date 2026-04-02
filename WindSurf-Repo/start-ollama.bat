@echo off
echo Starting BYOS Backend with Ollama...
echo.

REM Check if Ollama is installed
where ollama >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Ollama is not installed!
    echo Please install Ollama from https://ollama.ai
    pause
    exit /b 1
)

echo ✅ Ollama is installed

REM Check if Ollama is running
curl -s http://127.0.0.1:11434/api/tags >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo 🚀 Starting Ollama...
    start "Ollama" ollama serve
    echo Waiting for Ollama to start...
    timeout /t 10 /nobreak >nul
    
    REM Check again
    curl -s http://127.0.0.1:11434/api/tags >nul 2>&1
    if %ERRORLEVEL% NEQ 0 (
        echo ❌ Failed to start Ollama
        pause
        exit /b 1
    )
)

echo ✅ Ollama is running

REM Check if model is installed
curl -s http://127.0.0.1:11434/api/tags | findstr "llama3.2:1b" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo 📦 Installing llama3.2:1b model...
    ollama pull llama3.2:1b
    if %ERRORLEVEL% NEQ 0 (
        echo ❌ Failed to install model
        pause
        exit /b 1
    )
)

echo ✅ Model llama3.2:1b is installed

REM Start BYOS Backend
echo.
echo 🚀 Starting BYOS Backend...
python byos-backend-single.py

pause
