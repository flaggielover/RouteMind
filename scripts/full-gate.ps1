[CmdletBinding()]
param(
    [switch] $KeepInfrastructure
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

Push-Location $root
try {
    & (Join-Path $PSScriptRoot "verify.ps1")

    if (Test-Path -LiteralPath "compose.yaml") {
        docker compose config --quiet
        if ($LASTEXITCODE -ne 0) {
            throw "Compose configuration validation failed"
        }
    }

    if (Test-Path -LiteralPath "services/business-api/mvnw.cmd") {
        & "services/business-api/mvnw.cmd" -q test
        if ($LASTEXITCODE -ne 0) {
            throw "Java tests failed"
        }
    }

    if (Test-Path -LiteralPath "services/compute-api/pyproject.toml") {
        python -m pytest services/compute-api
        if ($LASTEXITCODE -ne 0) {
            throw "Python tests failed"
        }
    }

    Write-Host "PASS: RouteMind full available gate"
}
finally {
    Pop-Location
}
