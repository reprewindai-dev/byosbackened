#requires -Version 5.0
<#
.SYNOPSIS
  Starts the BYOS API server. Idempotent — kills any existing instance first.

.DESCRIPTION
  - Activates the local Python (uses system python by default; edit $PythonExe if you have a venv)
  - Kills any existing uvicorn on port 8000
  - Starts uvicorn bound to 127.0.0.1:8000 with sane production-ish flags
  - Logs to server.log (rotated daily by date)

.NOTES
  Run manually:   powershell -ExecutionPolicy Bypass -File .\start_server.ps1
  Run at boot:    install_autostart.ps1 (registers a Task Scheduler task)
#>

param(
    [string]$BindHost = "127.0.0.1",
    [int]$Port = 8000,
    [string]$PythonExe = "python"
)

$ErrorActionPreference = "Continue"
$BackendDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $BackendDir

# ── Kill anything already on the port ────────────────────────────────────────
$existing = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($existing) {
    foreach ($conn in $existing) {
        try {
            Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue
            Write-Host "Killed existing process on port $Port (PID $($conn.OwningProcess))"
        } catch {}
    }
    Start-Sleep -Seconds 1
}

# ── Log file (one per day) ──────────────────────────────────────────────────
$LogDir = Join-Path $BackendDir "logs"
if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir | Out-Null }
$LogFile = Join-Path $LogDir ("server-{0}.log" -f (Get-Date -Format "yyyy-MM-dd"))

# ── Env ─────────────────────────────────────────────────────────────────────
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUNBUFFERED = "1"

# ── Launch uvicorn ──────────────────────────────────────────────────────────
$Args = @(
    "-m", "uvicorn",
    "apps.api.main:app",
    "--host", $BindHost,
    "--port", $Port,
    "--log-level", "info",
    "--backlog", "2048",
    "--limit-concurrency", "2000",
    "--timeout-keep-alive", "65"
)

Write-Host "Starting BYOS API on ${BindHost}:${Port}"
Write-Host "Logs: $LogFile"

# Append to log; redirect both stdout and stderr
& $PythonExe @Args *>> $LogFile
