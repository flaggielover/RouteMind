[CmdletBinding()]
param(
    [ValidateRange(60, 900)]
    [int] $TimeoutSeconds = 240
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$pwsh = (Get-Command pwsh -ErrorAction SilentlyContinue).Source
if (-not $pwsh) { $pwsh = (Get-Command powershell -ErrorAction Stop).Source }
$python = (Get-Command python -ErrorAction Stop).Source
$businessLog = Join-Path ([System.IO.Path]::GetTempPath()) "routemind-business-performance.log"
$businessErrorLog = Join-Path ([System.IO.Path]::GetTempPath()) "routemind-business-performance.err.log"
$computeLog = Join-Path ([System.IO.Path]::GetTempPath()) "routemind-compute-performance.log"
$computeErrorLog = Join-Path ([System.IO.Path]::GetTempPath()) "routemind-compute-performance.err.log"
$started = @()

function Wait-Health {
    param([string] $Uri, [string] $ExpectedStatus)
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        try {
            $response = Invoke-RestMethod -Uri $Uri -TimeoutSec 5
            if ($response.status -eq $ExpectedStatus) { return }
        }
        catch { }
        Start-Sleep -Seconds 2
    } while ((Get-Date) -lt $deadline)
    throw "Health check did not become ready: $Uri"
}

function Stop-Tree {
    param($Process)
    if ($Process -and -not $Process.HasExited) {
        & taskkill /PID $Process.Id /T /F 2>$null | Out-Null
    }
}

function Show-Logs {
    foreach ($log in @($businessLog, $businessErrorLog, $computeLog, $computeErrorLog)) {
        if (Test-Path -LiteralPath $log) {
            Write-Host "--- $log (tail) ---"
            Get-Content -LiteralPath $log -Tail 50
        }
    }
}

try {
    & (Join-Path $PSScriptRoot "infra.ps1") -Action up -TimeoutSeconds 120
    Remove-Item -LiteralPath $businessLog, $businessErrorLog, $computeLog, $computeErrorLog -Force -ErrorAction SilentlyContinue
    $business = Start-Process -FilePath $pwsh -ArgumentList @(
        "-NoProfile", "-File", (Join-Path $PSScriptRoot "business-api.ps1"), "-Action", "run"
    ) -WorkingDirectory $root -Environment @{ ROUTEMIND_REDIS_PROJECTION_ENABLED = "true" } `
        -RedirectStandardOutput $businessLog -RedirectStandardError $businessErrorLog -PassThru -WindowStyle Hidden
    $compute = Start-Process -FilePath $pwsh -ArgumentList @(
        "-NoProfile", "-File", (Join-Path $PSScriptRoot "compute-api.ps1"), "-Action", "run"
    ) -WorkingDirectory $root -RedirectStandardOutput $computeLog -RedirectStandardError $computeErrorLog -PassThru -WindowStyle Hidden
    $started += $business
    $started += $compute
    Wait-Health "http://127.0.0.1:18080/actuator/health" "UP"
    Wait-Health "http://127.0.0.1:18081/healthz" "UP"
    Write-Host "PASS: Java and Python health probes"
    & $python (Join-Path $PSScriptRoot "performance-realtime-gate.py")
    if ($LASTEXITCODE -ne 0) { throw "performance/realtime measurement failed with exit code $LASTEXITCODE" }
    Write-Host "PASS: RM-180 performance and realtime resilience gate"
}
catch {
    Show-Logs
    throw
}
finally {
    foreach ($process in $started) { Stop-Tree $process }
}
