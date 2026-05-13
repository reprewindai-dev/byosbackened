param(
    [string]$SshKeyPath = "$HOME/.ssh/veklom-deploy",
    [string]$Server1 = "5.78.135.11",
    [string]$Server2 = "5.78.153.146"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Section {
    param([string]$Title)
    Write-Host ""
    Write-Host "=== $Title ==="
}

function Invoke-Remote {
    param(
        [string]$HostName,
        [string]$Command
    )

    ssh -F NUL -i $SshKeyPath -o StrictHostKeyChecking=accept-new "root@$HostName" $Command
}

function Test-HttpJson {
    param([string]$Url)

    try {
        $response = Invoke-RestMethod -Uri $Url -Method Get -TimeoutSec 15
        [pscustomobject]@{
            url = $Url
            ok = $true
            payload = ($response | ConvertTo-Json -Compress -Depth 6)
        }
    } catch {
        [pscustomobject]@{
            url = $Url
            ok = $false
            payload = $_.Exception.Message
        }
    }
}

Write-Section "Public health"
$healthChecks = @(
    (Test-HttpJson -Url "https://api.veklom.com/health")
    Test-HttpJson -Url "https://license.veklom.com/health"
)
$healthChecks | Format-Table -AutoSize

Write-Section "Server 1 containers"
Invoke-Remote -HostName $Server1 -Command "docker ps -a --format 'table {{.ID}}\t{{.Image}}\t{{.Status}}\t{{.Names}}\t{{.Ports}}'"

Write-Section "Live veklom-api container"
$liveContainerId = (Invoke-Remote -HostName $Server1 -Command "docker ps -q --filter label=coolify.resourceName=veklom-api").Trim()
if (-not $liveContainerId) {
    throw "Unable to resolve live veklom-api container on $Server1"
}
Invoke-Remote -HostName $Server1 -Command "docker inspect $liveContainerId --format '{{json .Config.Labels}}'"

Write-Section "Restarting Coolify artifacts"
$restarting = Invoke-Remote -HostName $Server1 -Command "docker ps -a --filter status=restarting --format '{{.ID}}\t{{.Image}}\t{{.Status}}\t{{.Names}}'"
if ([string]::IsNullOrWhiteSpace($restarting)) {
    Write-Host "No restarting containers found."
} else {
    $restarting
    foreach ($line in ($restarting -split "`n")) {
        if ([string]::IsNullOrWhiteSpace($line)) {
            continue
        }
        $containerId = ($line -split "`t")[0].Trim()
        if (-not $containerId) {
            continue
        }
        Write-Section "Logs for restarting container $containerId"
        Invoke-Remote -HostName $Server1 -Command "docker logs $containerId --tail 80"
    }
}

Write-Section "Live alembic state"
Invoke-Remote -HostName $Server1 -Command "docker exec $liveContainerId sh -lc 'alembic current && alembic heads'"

Write-Section "Live env presence"
Invoke-Remote -HostName $Server1 -Command "docker exec $liveContainerId sh -lc 'env | sort'" |
    Select-String '^(LICENSE|BUYER_DOWNLOAD|APP_VERSION|STRIPE|ALERT_|SECRET_KEY|ENCRYPTION_KEY|DATABASE_URL|REDIS_URL)=' |
    ForEach-Object { $_.ToString() -replace '=.*', '=<set>' }

Write-Section "Server 2 containers"
Invoke-Remote -HostName $Server2 -Command "docker ps -a --format 'table {{.ID}}\t{{.Image}}\t{{.Status}}\t{{.Names}}\t{{.Ports}}'"

Write-Section "License server labels"
Invoke-Remote -HostName $Server2 -Command "docker inspect veklom-license-server --format '{{json .Config.Labels}}'"
