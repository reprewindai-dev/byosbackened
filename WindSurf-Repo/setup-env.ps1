# Environment Variable Management Script for Windows PowerShell
# Generates secure secrets and manages environment configuration

Write-Host "🔐 Managing environment variables for Sovereign AI SaaS..."

# Check if .env file exists
if (-not (Test-Path ".env.production")) {
    Write-Host "❌ .env.production file not found!" -ForegroundColor Red
    exit 1
}

# Backup original file
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
Copy-Item ".env.production" ".env.production.backup.$timestamp"

Write-Host "🔄 Generating secure environment variables..."

# Generate secrets using .NET cryptography
$random = [System.Security.Cryptography.RandomNumberGenerator]::Create()
$bytes = New-Object byte[] 64
$random.GetBytes($bytes)
$SECRET_KEY = [System.Convert]::ToBase64String($bytes) -replace '[+/=]', '' | Substring(0, 64)

$bytes = New-Object byte[] 64
$random.GetBytes($bytes)
$AI_CITIZENSHIP_SECRET = [System.Convert]::ToBase64String($bytes) -replace '[+/=]', '' | Substring(0, 64)

$bytes = New-Object byte[] 32
$random.GetBytes($bytes)
$POSTGRES_PASSWORD = [System.Convert]::ToBase64String($bytes) -replace '[+/=]', '' | Substring(0, 32)

$bytes = New-Object byte[] 32
$random.GetBytes($bytes)
$REDIS_PASSWORD = [System.Convert]::ToBase64String($bytes) -replace '[+/=]', '' | Substring(0, 32)

$bytes = New-Object byte[] 32
$random.GetBytes($bytes)
$GRAFANA_PASSWORD = [System.Convert]::ToBase64String($bytes) -replace '[+/=]', '' | Substring(0, 32)

$bytes = New-Object byte[] 64
$random.GetBytes($bytes)
$STRIPE_WEBHOOK_SECRET = [System.Convert]::ToBase64String($bytes) -replace '[+/=]', '' | Substring(0, 64)

# Get current domain or use IP
if ($args.Count -eq 0) {
    try {
        $IP = Invoke-RestMethod -Uri "http://checkip.amazonaws.com" -TimeoutSec 10
        $DOMAIN = "$IP.nip.io"
    } catch {
        $DOMAIN = "localhost"
    }
} else {
    $DOMAIN = $args[0]
}

Write-Host "🌐 Using domain: $DOMAIN"

# Update .env.production file
$content = Get-Content ".env.production"
$content = $content -replace 'your-super-secure-64-character-random-secret-key-here-change-this', $SECRET_KEY
$content = $content -replace 'your-ai-citizenship-secret-key-here-change-this', $AI_CITIZENSHIP_SECRET
$content = $content -replace 'your-secure-postgres-password-here', $POSTGRES_PASSWORD
$content = $content -replace 'your-secure-redis-password-here', $REDIS_PASSWORD
$content = $content -replace 'your-secure-grafana-password-here', $GRAFANA_PASSWORD
$content = $content -replace 'your-domain.com', $DOMAIN
$content | Set-Content ".env.production"

# Add additional secure variables
Add-Content ".env.production" ""
Add-Content ".env.production" "# Additional Security Variables"
Add-Content ".env.production" "STRIPE_WEBHOOK_SECRET=$STRIPE_WEBHOOK_SECRET"
Add-Content ".env.production" "SESSION_SECRET=$SECRET_KEY"
Add-Content ".env.production" "CSRF_SECRET=$AI_CITIZENSHIP_SECRET"
Add-Content ".env.production" "ENCRYPTION_KEY=$SECRET_KEY"

Add-Content ".env.production" ""
Add-Content ".env.production" "# LLM Configuration"
Add-Content ".env.production" "MODEL_CACHE_DIR=/app/models"
Add-Content ".env.production" "MAX_CONCURRENT_REQUESTS=10"
Add-Content ".env.production" "MODEL_MAX_LENGTH=4096"
Add-Content ".env.production" "GPU_MEMORY_FRACTION=0.8"
Add-Content ".env.production" "CUDA_VISIBLE_DEVICES=0"

Add-Content ".env.production" ""
Add-Content ".env.production" "# Performance Tuning"
Add-Content ".env.production" "OMP_NUM_THREADS=4"
Add-Content ".env.production" "TOKENIZERS_PARALLELISM=false"

Add-Content ".env.production" ""
Add-Content ".env.production" "# Monitoring"
Add-Content ".env.production" "SENTRY_DSN=your-sentry-dsn-here"
Add-Content ".env.production" "LOG_LEVEL=INFO"
Add-Content ".env.production" "LOG_FORMAT=json"

Add-Content ".env.production" ""
Add-Content ".env.production" "# Backup Configuration"
Add-Content ".env.production" "BACKUP_SCHEDULE=0 2 * * *"
Add-Content ".env.production" "BACKUP_RETENTION_DAYS=30"
Add-Content ".env.production" "BACKUP_ENCRYPTION_KEY=$SECRET_KEY"

Add-Content ".env.production" ""
Add-Content ".env.production" "# SSL Configuration"
Add-Content ".env.production" "SSL_CERT_PATH=/app/infra/docker/ssl/cert.pem"
Add-Content ".env.production" "SSL_KEY_PATH=/app/infra/docker/ssl/key.pem"

Write-Host "✅ Environment variables generated successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "🔑 Generated secrets:"
Write-Host "- SECRET_KEY: $($SECRET_KEY.Substring(0,16))..."
Write-Host "- AI_CITIZENSHIP_SECRET: $($AI_CITIZENSHIP_SECRET.Substring(0,16))..."
Write-Host "- POSTGRES_PASSWORD: $($POSTGRES_PASSWORD.Substring(0,8))..."
Write-Host "- REDIS_PASSWORD: $($REDIS_PASSWORD.Substring(0,8))..."
Write-Host "- GRAFANA_PASSWORD: $($GRAFANA_PASSWORD.Substring(0,8))..."
Write-Host ""
Write-Host "⚠️  Please update the following variables manually:"
Write-Host "- HUGGINGFACE_API_KEY"
Write-Host "- OPENAI_API_KEY"
Write-Host "- STRIPE_SECRET_KEY"
Write-Host "- STRIPE_PUBLISHABLE_KEY"
Write-Host "- SENTRY_DSN (if using Sentry)"
Write-Host ""
Write-Host "📋 Environment file updated: .env.production"
Write-Host "Backup created: .env.production.backup.$timestamp" -ForegroundColor Green

# Create .env.local for development
Write-Host "📝 Creating .env.local for development..."
"# Development Environment" | Out-File -FilePath ".env.local" -Encoding utf8
"ENVIRONMENT=development" | Out-File -FilePath ".env.local" -Append -Encoding utf8
"DEBUG=true" | Out-File -FilePath ".env.local" -Append -Encoding utf8
"SECRET_KEY=$SECRET_KEY" | Out-File -FilePath ".env.local" -Append -Encoding utf8
"AI_CITIZENSHIP_SECRET=$AI_CITIZENSHIP_SECRET" | Out-File -FilePath ".env.local" -Append -Encoding utf8
"DATABASE_URL=sqlite:///./local.db" | Out-File -FilePath ".env.local" -Append -Encoding utf8
"REDIS_URL=redis://localhost:6379/0" | Out-File -FilePath ".env.local" -Append -Encoding utf8
"FRONTEND_URL=http://localhost:3000" | Out-File -FilePath ".env.local" -Append -Encoding utf8
"API_URL=http://localhost:8000" | Out-File -FilePath ".env.local" -Append -Encoding utf8
"LOG_LEVEL=DEBUG" | Out-File -FilePath ".env.local" -Append -Encoding utf8

Write-Host "✅ Development environment created: .env.local" -ForegroundColor Green
