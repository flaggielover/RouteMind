[CmdletBinding()]
param(
    [ValidateSet("check", "e2e")]
    [string] $Action = "check"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$webRoot = Join-Path $root "apps/web"
$env:NPM_CONFIG_CACHE = Join-Path $root ".tools/npm-cache"

if (-not (Test-Path -LiteralPath (Join-Path $webRoot "package.json") -PathType Leaf)) {
    throw "Web application package is missing: $webRoot"
}
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    throw "npm is required for the web gate"
}

function Invoke-NpmScript([string] $scriptName) {
    npm run $scriptName
    if ($LASTEXITCODE -ne 0) {
        throw "Web npm script failed: $scriptName"
    }
}

Push-Location $webRoot
try {
    if ($Action -eq "check") {
        Invoke-NpmScript "format:check"
        Invoke-NpmScript "lint"
        Invoke-NpmScript "typecheck"
        Invoke-NpmScript "test:unit"
        Invoke-NpmScript "build"
        Write-Host "PASS: RouteMind web static and unit gate"
    }
    else {
        Invoke-NpmScript "test:e2e"
        Write-Host "PASS: RouteMind web browser smoke gate"
    }
}
finally {
    Pop-Location
}
