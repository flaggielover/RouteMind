[CmdletBinding()]
param(
    [switch] $Infrastructure,
    [switch] $KeepInfrastructure
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$infrastructureWasRunning = $false

Push-Location $root
try {
    & (Join-Path $PSScriptRoot "verify.ps1")

    if ($Infrastructure) {
        $runningServices = @(docker compose ps --status running -q)
        if ($LASTEXITCODE -ne 0) {
            throw "Unable to inspect existing infrastructure state"
        }
        $infrastructureWasRunning = $runningServices.Count -gt 0
        & (Join-Path $PSScriptRoot "infra.ps1") -Action up
    }

    if (Test-Path -LiteralPath "services/business-api/mvnw.cmd") {
        & (Join-Path $PSScriptRoot "business-api.ps1") -Action test
    }

    if (Test-Path -LiteralPath "services/compute-api/pyproject.toml") {
        & (Join-Path $PSScriptRoot "compute-api.ps1") -Action check
    }

    if (Test-Path -LiteralPath "apps/web/package.json") {
        & (Join-Path $PSScriptRoot "web.ps1") -Action check
    }

    Write-Host "PASS: RouteMind full available gate"
}
finally {
    if ($Infrastructure -and -not $KeepInfrastructure -and -not $infrastructureWasRunning) {
        & (Join-Path $PSScriptRoot "infra.ps1") -Action down
    }
    Pop-Location
}
