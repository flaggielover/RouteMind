[CmdletBinding()]
param(
    [ValidateSet("sync", "test", "check", "run", "lock", "resilience")]
    [string] $Action = "check"
)

$ErrorActionPreference = "Stop"
$uvVersion = "0.12.5"
$root = Split-Path -Parent $PSScriptRoot
$serviceRoot = Join-Path $root "services/compute-api"
$toolRoot = Join-Path $root ".tools/uv"
$onWindows = [System.Environment]::OSVersion.Platform -eq [System.PlatformID]::Win32NT
$toolBin = if ($onWindows) { Join-Path $toolRoot "Scripts" } else { Join-Path $toolRoot "bin" }
$toolPython = Join-Path $toolBin $(if ($onWindows) { "python.exe" } else { "python" })
$uv = Join-Path $toolBin $(if ($onWindows) { "uv.exe" } else { "uv" })

function Get-RepositoryPython {
    $python = Get-Command python -ErrorAction SilentlyContinue
    if (-not $python) {
        throw "Python 3.12 or newer is required"
    }

    $versionText = & $python.Source -c "import platform; print(platform.python_version())"
    if ($LASTEXITCODE -ne 0 -or $versionText -notmatch '^(\d+)\.(\d+)') {
        throw "Unable to inspect Python at $($python.Source)"
    }

    $major = [int]$Matches[1]
    $minor = [int]$Matches[2]
    if ($major -ne 3 -or $minor -lt 12 -or $minor -ge 15) {
        throw "Python 3.12 through 3.14 is required; found $versionText"
    }

    return $python.Source
}

function Initialize-Uv([string] $PythonPath) {
    $installedVersion = $null
    if (Test-Path -LiteralPath $uv) {
        $installedVersion = ((& $uv --version) -split '\s+')[1]
    }

    if ($installedVersion -eq $uvVersion) {
        return
    }

    & $PythonPath -m venv --clear $toolRoot
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to create the isolated uv tool environment"
    }

    & $toolPython -m pip install --disable-pip-version-check --no-input "uv==$uvVersion"
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to install uv $uvVersion"
    }
}

function Invoke-Uv([string[]] $Arguments) {
    & $uv @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "uv command failed: $($Arguments -join ' ')"
    }
}

if (-not (Test-Path -LiteralPath (Join-Path $serviceRoot "pyproject.toml"))) {
    throw "Compute API pyproject.toml is missing"
}

$pythonPath = Get-RepositoryPython
Initialize-Uv $pythonPath
$env:UV_LINK_MODE = "copy"
$runtimeVersion = & $pythonPath --version
Write-Host "Using $runtimeVersion and uv $uvVersion"

Push-Location $serviceRoot
try {
    switch ($Action) {
        "lock" { Invoke-Uv @("lock", "--python", $pythonPath) }
        "sync" { Invoke-Uv @("sync", "--frozen", "--python", $pythonPath) }
        "test" {
            Invoke-Uv @("sync", "--frozen", "--python", $pythonPath)
            Invoke-Uv @("run", "--frozen", "pytest")
        }
        "check" {
            Invoke-Uv @("sync", "--frozen", "--python", $pythonPath)
            Invoke-Uv @("run", "--frozen", "ruff", "check", ".", "../../scripts/validate_contracts.py")
            Invoke-Uv @("run", "--frozen", "ruff", "format", "--check", ".", "../../scripts/validate_contracts.py")
            Invoke-Uv @("run", "--frozen", "mypy", "src", "tests", "../../scripts/validate_contracts.py")
            Invoke-Uv @("run", "--frozen", "python", "../../scripts/validate_contracts.py")
            Invoke-Uv @("run", "--frozen", "pytest")
            Invoke-Uv @("run", "--frozen", "python", "../../scripts/determinism_gate.py")
            Invoke-Uv @("run", "--frozen", "python", "../../scripts/analytics_archive_gate.py")
        }
        "run" {
            Invoke-Uv @("sync", "--frozen", "--python", $pythonPath)
            Invoke-Uv @("run", "--frozen", "routemind-compute-api")
        }
        "resilience" {
            Invoke-Uv @("sync", "--frozen", "--python", $pythonPath)
            Invoke-Uv @("run", "--frozen", "pytest", "tests/test_resilience.py", "--no-cov")
        }
    }
}
finally {
    Pop-Location
}
