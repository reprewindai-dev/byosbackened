@echo off
REM Environment Variable Management Script for Windows
REM Generates secure secrets and manages environment configuration

echo 🔐 Managing environment variables for Sovereign AI SaaS...

REM Check if .env file exists
if not exist ".env.production" (
    echo ❌ .env.production file not found!
    exit /b 1
)

REM Backup original file
for /f "tokens=2 delims==" %%a in ('wmic OS Get localdatetime /value') do set "dt=%%a"
set "YYYY=%dt:~0,4%"
set "MM=%dt:~4,2%"
set "DD=%dt:~6,2%"
set "HH=%dt:~8,2%"
set "Min=%dt:~10,2%"
set "Sec=%dt:~12,2%"
set "timestamp=%YYYY%%MM%%DD%_%HH%%Min%%Sec%"

copy ".env.production" ".env.production.backup.%timestamp%"

echo 🔄 Generating secure environment variables...

REM Generate secrets using PowerShell
for /f %%i in ('powershell -Command "openssl rand -base64 64 ^| tr -d '=+/' ^| cut -c1-64"') do set SECRET_KEY=%%i
for /f %%i in ('powershell -Command "openssl rand -base64 64 ^| tr -d '=+/' ^| cut -c1-64"') do set AI_CITIZENSHIP_SECRET=%%i
for /f %%i in ('powershell -Command "openssl rand -base64 32 ^| tr -d '=+/' ^| cut -c1-32"') do set POSTGRES_PASSWORD=%%i
for /f %%i in ('powershell -Command "openssl rand -base64 32 ^| tr -d '=+/' ^| cut -c1-32"') do set REDIS_PASSWORD=%%i
for /f %%i in ('powershell -Command "openssl rand -base64 32 ^| tr -d '=+/' ^| cut -c1-32"') do set GRAFANA_PASSWORD=%%i
for /f %%i in ('powershell -Command "openssl rand -base64 64 ^| tr -d '=+/' ^| cut -c1-64"') do set STRIPE_WEBHOOK_SECRET=%%i

REM Get current domain or use IP
if "%~1"=="" (
    for /f %%i in ('curl -s http://checkip.amazonaws.com') do set IP=%%i
    set DOMAIN=%IP%.nip.io
) else (
    set DOMAIN=%1
)

echo 🌐 Using domain: %DOMAIN%

REM Update .env.production file using PowerShell
powershell -Command "(Get-Content .env.production) -replace 'your-super-secure-64-character-random-secret-key-here-change-this', '%SECRET_KEY%' | Set-Content .env.production"
powershell -Command "(Get-Content .env.production) -replace 'your-ai-citizenship-secret-key-here-change-this', '%AI_CITIZENSHIP_SECRET%' | Set-Content .env.production"
powershell -Command "(Get-Content .env.production) -replace 'your-secure-postgres-password-here', '%POSTGRES_PASSWORD%' | Set-Content .env.production"
powershell -Command "(Get-Content .env.production) -replace 'your-secure-redis-password-here', '%REDIS_PASSWORD%' | Set-Content .env.production"
powershell -Command "(Get-Content .env.production) -replace 'your-secure-grafana-password-here', '%GRAFANA_PASSWORD%' | Set-Content .env.production"
powershell -Command "(Get-Content .env.production) -replace 'your-domain.com', '%DOMAIN%' | Set-Content .env.production"

REM Add additional secure variables
echo # Additional Security Variables >> .env.production
echo STRIPE_WEBHOOK_SECRET=%STRIPE_WEBHOOK_SECRET% >> .env.production
echo SESSION_SECRET=%SECRET_KEY% >> .env.production
echo CSRF_SECRET=%AI_CITIZENSHIP_SECRET% >> .env.production
echo ENCRYPTION_KEY=%SECRET_KEY% >> .env.production
echo. >> .env.production
echo # LLM Configuration >> .env.production
echo MODEL_CACHE_DIR=/app/models >> .env.production
echo MAX_CONCURRENT_REQUESTS=10 >> .env.production
echo MODEL_MAX_LENGTH=4096 >> .env.production
echo GPU_MEMORY_FRACTION=0.8 >> .env.production
echo CUDA_VISIBLE_DEVICES=0 >> .env.production
echo. >> .env.production
echo # Performance Tuning >> .env.production
echo OMP_NUM_THREADS=4 >> .env.production
echo TOKENIZERS_PARALLELISM=false >> .env.production
echo. >> .env.production
echo # Monitoring >> .env.production
echo SENTRY_DSN=your-sentry-dsn-here >> .env.production
echo LOG_LEVEL=INFO >> .env.production
echo LOG_FORMAT=json >> .env.production
echo. >> .env.production
echo # Backup Configuration >> .env.production
echo BACKUP_SCHEDULE=0 2 * * * >> .env.production
echo BACKUP_RETENTION_DAYS=30 >> .env.production
echo BACKUP_ENCRYPTION_KEY=%SECRET_KEY% >> .env.production
echo. >> .env.production
echo # SSL Configuration >> .env.production
echo SSL_CERT_PATH=/app/infra/docker/ssl/cert.pem >> .env.production
echo SSL_KEY_PATH=/app/infra/docker/ssl/key.pem >> .env.production

echo ✅ Environment variables generated successfully!
echo.
echo 🔑 Generated secrets:
echo - SECRET_KEY: %SECRET_KEY:~0,16%...
echo - AI_CITIZENSHIP_SECRET: %AI_CITIZENSHIP_SECRET:~0,16%...
echo - POSTGRES_PASSWORD: %POSTGRES_PASSWORD:~0,8%...
echo - REDIS_PASSWORD: %REDIS_PASSWORD:~0,8%...
echo - GRAFANA_PASSWORD: %GRAFANA_PASSWORD:~0,8%...
echo.
echo ⚠️  Please update the following variables manually:
echo - HUGGINGFACE_API_KEY
echo - OPENAI_API_KEY
echo - STRIPE_SECRET_KEY
echo - STRIPE_PUBLISHABLE_KEY
echo - SENTRY_DSN (if using Sentry)
echo.
echo 📋 Environment file updated: .env.production
echo 💾 Backup created: .env.production.backup.%timestamp%

REM Create .env.local for development
echo 📝 Creating .env.local for development...
echo # Development Environment > .env.local
echo ENVIRONMENT=development >> .env.local
echo DEBUG=true >> .env.local
echo SECRET_KEY=%SECRET_KEY% >> .env.local
echo AI_CITIZENSHIP_SECRET=%AI_CITIZENSHIP_SECRET% >> .env.local
echo DATABASE_URL=sqlite:///./local.db >> .env.local
echo REDIS_URL=redis://localhost:6379/0 >> .env.local
echo FRONTEND_URL=http://localhost:3000 >> .env.local
echo API_URL=http://localhost:8000 >> .env.local
echo LOG_LEVEL=DEBUG >> .env.local

echo ✅ Development environment created: .env.local
