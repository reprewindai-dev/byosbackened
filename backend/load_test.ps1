# Load Test Runner for BYOS Backend
# Usage: .\load_test.ps1 -ApiKey "byos_your_key" -Users 10 -Duration 60

param(
    [string]$ApiKey = $env:BYOS_API_KEY,
    [int]$Users = 10,
    [int]$Duration = 60,
    [string]$Host = "http://localhost:8000"
)

if (-not $ApiKey) {
    Write-Host "❌ Error: API key required. Set BYOS_API_KEY environment variable or pass -ApiKey parameter" -ForegroundColor Red
    Write-Host "   Example: .\load_test.ps1 -ApiKey 'byos_your_key_here'" -ForegroundColor Yellow
    exit 1
}

Write-Host "🚀 Starting Locust Load Test" -ForegroundColor Green
Write-Host "   Host: $Host" -ForegroundColor Cyan
Write-Host "   Users: $Users" -ForegroundColor Cyan
Write-Host "   Duration: ${Duration}s" -ForegroundColor Cyan
Write-Host ""

# Check if locust is installed
try {
    $locustVersion = locust --version 2>&1
    Write-Host "✅ Locust found: $locustVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Locust not found. Installing..." -ForegroundColor Yellow
    pip install locust
}

Write-Host ""
Write-Host "🧪 Starting load test..." -ForegroundColor Green
Write-Host "   Web UI: http://localhost:8089" -ForegroundColor Cyan
Write-Host ""

# Run locust
$env:BYOS_API_KEY = $ApiKey
locust -f locustfile.py --host $Host --users $Users --spawn-rate 5 --run-time "${Duration}s" --headless --html load_test_report.html

Write-Host ""
Write-Host "✅ Load test complete!" -ForegroundColor Green
Write-Host "   Report saved to: load_test_report.html" -ForegroundColor Cyan
