[CmdletBinding()]
param(
    [ValidateSet("run")]
    [string] $Action = "run"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$webRoot = Join-Path $root "apps/web"
if (-not (Test-Path -LiteralPath (Join-Path $webRoot "package.json") -PathType Leaf)) {
    throw "Web application package is missing: $webRoot"
}
Push-Location $webRoot
try {
    npm run dev -- --host 127.0.0.1
    if ($LASTEXITCODE -ne 0) { throw "Web development server failed with exit code $LASTEXITCODE" }
}
finally {
    Pop-Location
}
