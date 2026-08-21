[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$envPath = Join-Path $root ".env"
$examplePath = Join-Path $root ".env.example"

if (-not (Test-Path -LiteralPath $examplePath -PathType Leaf)) {
    throw ".env.example is missing"
}

if (-not (Test-Path -LiteralPath $envPath)) {
    Copy-Item -LiteralPath $examplePath -Destination $envPath
    Write-Host "Created .env from .env.example"
}
else {
    Write-Host "Kept existing .env"
}

& (Join-Path $PSScriptRoot "doctor.ps1")
if ($LASTEXITCODE -ne 0) {
    throw "Required development prerequisites are missing"
}

& (Join-Path $PSScriptRoot "verify.ps1")
