[CmdletBinding()]
param()

$ErrorActionPreference = "Continue"
$requiredFailures = 0

function Test-Tool {
    param(
        [Parameter(Mandatory)] [string] $Name,
        [Parameter(Mandatory)] [string] $Command,
        [switch] $Required
    )

    $found = Get-Command $Command -ErrorAction SilentlyContinue
    if ($found) {
        Write-Host "PASS  $Name ($($found.Source))"
    }
    else {
        $label = if ($Required) { "FAIL" } else { "WARN" }
        Write-Host "$label  $Name not found"
        if ($Required) {
            $script:requiredFailures += 1
        }
    }
}

Test-Tool -Name "Git" -Command "git" -Required
Test-Tool -Name "Python" -Command "python" -Required
Test-Tool -Name "Java" -Command "java"
Test-Tool -Name "Node.js" -Command "node"
Test-Tool -Name "Docker" -Command "docker"

if (Get-Command docker -ErrorAction SilentlyContinue) {
    docker compose version | Out-Host
    if ($LASTEXITCODE -ne 0) {
        Write-Host "WARN  Docker Compose plugin is unavailable"
    }
}

$root = Split-Path -Parent $PSScriptRoot
$siblingData = Join-Path (Split-Path -Parent $root) "RouteMind-Data"
$configuredData = [Environment]::GetEnvironmentVariable("ROUTEMIND_DATA_ROOT")
$dataRoot = if ($configuredData) { $configuredData } elseif (Test-Path $siblingData) { $siblingData } else { $null }
if ($dataRoot -and (Test-Path -LiteralPath $dataRoot -PathType Container)) {
    Write-Host "PASS  RouteMind data root ($dataRoot)"
}
else {
    Write-Host "WARN  RouteMind data root not discovered; set ROUTEMIND_DATA_ROOT"
}

if ($requiredFailures -gt 0) {
    exit 1
}
