[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

& (Join-Path $PSScriptRoot "business-api.ps1") -Action resilience
if ($LASTEXITCODE -ne 0) {
    throw "Java bounded-degradation gate failed"
}

& (Join-Path $PSScriptRoot "compute-api.ps1") -Action resilience
if ($LASTEXITCODE -ne 0) {
    throw "Python bounded-degradation gate failed"
}

Write-Host "PASS: RouteMind bounded degradation and failure injection gate"
