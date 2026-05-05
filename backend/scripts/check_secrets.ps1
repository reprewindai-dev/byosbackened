# Pre-commit secret scanner for Veklom backend.
# Run manually:
#   pwsh ./scripts/check_secrets.ps1
# Or wire into git via Husky / a manual pre-commit hook.
#
# Catches:
#   sk_live_  sk_test_  rk_live_  rk_test_   (Stripe)
#   whsec_                                    (Stripe webhook secrets)
#   AKIA[0-9A-Z]{16}                          (AWS access key IDs)
#   ghp_[A-Za-z0-9]{36}                       (GitHub personal access tokens)
#   AIza[0-9A-Za-z_-]{35}                     (Google API keys)
#   xox[baprs]-[A-Za-z0-9-]{10,}              (Slack tokens)
#   cfat_                                     (Cloudflare API tokens)
#   gsk_                                      (Groq API keys)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path "$PSScriptRoot/../..").Path
Set-Location $repoRoot

$patterns = @(
  '\bsk_(live|test)_[A-Za-z0-9]{20,}',
  '\brk_(live|test)_[A-Za-z0-9]{20,}',
  '\bwhsec_[A-Za-z0-9]{20,}',
  '\bAKIA[0-9A-Z]{16}\b',
  '\bghp_[A-Za-z0-9]{36}\b',
  '\bAIza[0-9A-Za-z_-]{35}\b',
  '\bxox[baprs]-[A-Za-z0-9-]{10,}',
  '\bcfat_[A-Za-z0-9_-]{20,}',
  '\bgsk_[A-Za-z0-9]{20,}'
)

# Skip known-safe / generated locations
$excludeDirs = @('node_modules', '.git', '.venv', 'venv', '__pycache__', '.pytest_cache', 'dist', 'build')
$excludeFiles = @('check_secrets.ps1', '*.lock', 'package-lock.json')

$found = 0
Get-ChildItem -Recurse -File | Where-Object {
    $rel = $_.FullName.Substring($repoRoot.Length).TrimStart('\','/')
    $skip = $false
    foreach ($d in $excludeDirs) { if ($rel -like "*$d*") { $skip = $true; break } }
    if (-not $skip) {
        foreach ($f in $excludeFiles) { if ($_.Name -like $f) { $skip = $true; break } }
    }
    -not $skip
} | ForEach-Object {
    $file = $_.FullName
    $content = Get-Content -Raw -LiteralPath $file -ErrorAction SilentlyContinue
    if (-not $content) { return }
    foreach ($pat in $patterns) {
        $matchResults = [regex]::Matches($content, $pat)
        foreach ($m in $matchResults) {
            $rel = $file.Substring($repoRoot.Length).TrimStart('\','/')
            Write-Host ("LEAK  " + $rel + "  -> " + $m.Value.Substring(0, [Math]::Min(20, $m.Value.Length)) + "...") -ForegroundColor Red
            $script:found++
        }
    }
}

if ($found -gt 0) {
    Write-Host "`n$found suspected secret(s) found. Roll any that are real, then remove from the file." -ForegroundColor Red
    exit 1
} else {
    Write-Host "OK - no secrets detected in source." -ForegroundColor Green
    exit 0
}
