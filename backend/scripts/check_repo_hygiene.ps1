# Repository hygiene guard for generated files and local secret/config files.
#
# This script intentionally checks tracked files, not the working tree. It is
# meant to stop generated artifacts and local secrets from entering Git history.

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path "$PSScriptRoot/../..").Path
Set-Location $repoRoot

$trackedFiles = git ls-files
$violations = New-Object System.Collections.Generic.List[string]

foreach ($path in $trackedFiles) {
    $normalized = $path -replace '\\', '/'

    if ($normalized -match '(^|/)__pycache__/') {
        $violations.Add("$normalized :: tracked Python cache directory")
        continue
    }

    if ($normalized -match '\.py[cod]$') {
        $violations.Add("$normalized :: tracked Python bytecode")
        continue
    }

    if ($normalized -match '(^|/)\.env($|\.)') {
        if ($normalized -notmatch '\.example$') {
            $violations.Add("$normalized :: tracked non-example env file")
            continue
        }
    }

    if ($normalized -match '(^|/)\.(aws|azure|gcloud|kube)/') {
        $violations.Add("$normalized :: tracked local cloud credential directory")
        continue
    }

    if ($normalized -match '(?i)(private[_-]?key|secret[_-]?key|api[_-]?token|cloudflare).*\.env$') {
        $violations.Add("$normalized :: tracked local secret-style env file")
        continue
    }
}

if ($violations.Count -gt 0) {
    Write-Host "Repository hygiene violations:" -ForegroundColor Red
    foreach ($violation in $violations) {
        Write-Host "BLOCK  $violation" -ForegroundColor Red
    }
    exit 1
}

Write-Host "OK - repository hygiene checks passed." -ForegroundColor Green
exit 0
