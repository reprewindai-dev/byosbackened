#!/usr/bin/env powershell
# Stress Test Runner - One command to rule them all
# Usage: .\run_stress_test.ps1 [users] [duration_seconds]

param(
    [int]$Users = 20,
    [int]$Duration = 60
)

$API_KEY = "byos_NDyIYuU6fsPJ-VRACGUsqRj-HXij3I0006tJ_nQWmoI"
$env:BYOS_API_KEY = $API_KEY

Write-Host ""
Write-Host "🚀 BYOS STRESS TEST SETUP" -ForegroundColor Green
Write-Host "==========================" -ForegroundColor Green
Write-Host ""

# Check if server is already running
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -Method GET -TimeoutSec 2 -ErrorAction Stop
    Write-Host "✅ Server already running on port 8000" -ForegroundColor Green
    $serverRunning = $true
} catch {
    Write-Host "🔄 Starting backend server..." -ForegroundColor Yellow
    $serverRunning = $false
}

# Start server if not running
if (-not $serverRunning) {
    Start-Process powershell -ArgumentList "-Command", "cd '$PWD'; uvicorn apps.api.main:app --host 0.0.0.0 --port 8000 --workers 1" -WindowStyle Normal
    Write-Host "⏳ Waiting for server to start..." -ForegroundColor Yellow
    Start-Sleep -Seconds 5
    
    # Verify server started
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -Method GET -TimeoutSec 5
        Write-Host "✅ Server started successfully" -ForegroundColor Green
    } catch {
        Write-Host "❌ Server failed to start. Check errors above." -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "🔑 API Key: $API_KEY" -ForegroundColor Cyan
Write-Host "👥 Users: $Users" -ForegroundColor Cyan
Write-Host "⏱️  Duration: ${Duration}s" -ForegroundColor Cyan
Write-Host ""
Write-Host "🧪 Starting stress test in 3 seconds..." -ForegroundColor Yellow
Write-Host "   (Press Ctrl+C to stop early)" -ForegroundColor Gray
Start-Sleep -Seconds 3
Write-Host ""

# Run locust
locust -f locustfile.py --host http://localhost:8000 --users $Users --spawn-rate 5 --run-time "${Duration}s" --headless

Write-Host ""
Write-Host "✅ Stress test complete!" -ForegroundColor Green
Write-Host ""
Write-Host "📊 To view detailed report:" -ForegroundColor Cyan
Write-Host "   locust -f locustfile.py --host http://localhost:8000" -ForegroundColor White
Write-Host "   (Then open http://localhost:8089 in browser)" -ForegroundColor Gray
Write-Host ""
