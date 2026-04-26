#requires -Version 5.0 -RunAsAdministrator
<#
.SYNOPSIS
  Installs a Windows Task Scheduler task that runs the BYOS API at boot.

.DESCRIPTION
  After running this once (as Administrator), the API will:
    - Start at every Windows boot, even before login
    - Restart automatically if it crashes (every 1 minute, up to 999 times)
    - Run silently in the background

  Idempotent — safe to re-run. Existing task is replaced.

.NOTES
  Install:    Run PowerShell as Administrator, then:
              powershell -ExecutionPolicy Bypass -File .\install_autostart.ps1

  Uninstall:  Unregister-ScheduledTask -TaskName "BYOS-API" -Confirm:$false

  Verify:     Get-ScheduledTask -TaskName "BYOS-API"
              Get-ScheduledTaskInfo -TaskName "BYOS-API"
#>

# Ensure admin
if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
        [Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Error "This script must be run as Administrator. Right-click PowerShell -> Run as Administrator."
    exit 1
}

$BackendDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$StartScript = Join-Path $BackendDir "start_server.ps1"
$TaskName = "BYOS-API"

if (-not (Test-Path $StartScript)) {
    Write-Error "start_server.ps1 not found at $StartScript"
    exit 1
}

# Remove old task if present
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue

# Action: run powershell with the start script
$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$StartScript`"" `
    -WorkingDirectory $BackendDir

# Trigger: at system startup (no login required)
$trigger = New-ScheduledTaskTrigger -AtStartup

# Settings: restart on failure, hidden, no time limit
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RestartCount 999 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit (New-TimeSpan -Days 0) `
    -Hidden

# Run as SYSTEM so it works without login
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest

# Register
Register-ScheduledTask -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Description "BYOS API — auto-starts at boot, restarts on failure"

Write-Host ""
Write-Host "✅ Task '$TaskName' installed." -ForegroundColor Green
Write-Host ""
Write-Host "Starting it now..."
Start-ScheduledTask -TaskName $TaskName
Start-Sleep -Seconds 5

# Quick health check
try {
    $r = Invoke-WebRequest "http://127.0.0.1:8000/health" -UseBasicParsing -TimeoutSec 3
    Write-Host "✅ API responding: HTTP $($r.StatusCode)" -ForegroundColor Green
} catch {
    Write-Host "⚠️  API not yet responding (may still be starting). Check logs/ folder." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Useful commands:"
Write-Host "  Status:    Get-ScheduledTaskInfo -TaskName '$TaskName'"
Write-Host "  Stop:      Stop-ScheduledTask -TaskName '$TaskName'"
Write-Host "  Start:     Start-ScheduledTask -TaskName '$TaskName'"
Write-Host "  Uninstall: Unregister-ScheduledTask -TaskName '$TaskName' -Confirm:`$false"
