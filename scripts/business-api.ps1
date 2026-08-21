[CmdletBinding()]
param(
    [ValidateSet("test", "package", "run")]
    [string] $Action = "test"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$serviceRoot = Join-Path $root "services/business-api"

function Set-RepositoryJavaHome {
    $java = Get-Command java -ErrorAction SilentlyContinue
    if (-not $java) {
        throw "Java 17 or newer is required"
    }

    $previousErrorAction = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $settings = & $java.Source -XshowSettings:properties -version 2>&1
    $javaExitCode = $LASTEXITCODE
    $ErrorActionPreference = $previousErrorAction
    if ($javaExitCode -ne 0) {
        throw "Unable to inspect Java runtime at $($java.Source)"
    }
    $homeLine = $settings | Where-Object { $_ -match '^\s*java\.home\s*=' } | Select-Object -First 1
    $versionLine = $settings | Where-Object { $_ -match '^\s*java\.version\s*=' } | Select-Object -First 1
    if (-not $homeLine -or -not $versionLine) {
        throw "Unable to discover Java home and version from $($java.Source)"
    }

    $javaHome = ($homeLine -replace '^\s*java\.home\s*=\s*', '').Trim()
    $javaVersion = ($versionLine -replace '^\s*java\.version\s*=\s*', '').Trim()
    $major = if ($javaVersion -match '^1\.(\d+)') { [int]$Matches[1] } elseif ($javaVersion -match '^(\d+)') { [int]$Matches[1] } else { 0 }
    if ($major -lt 17 -or -not (Test-Path -LiteralPath (Join-Path $javaHome "bin/javac.exe"))) {
        throw "A full JDK 17 or newer is required; found Java $javaVersion at $javaHome"
    }

    $env:JAVA_HOME = $javaHome
    Write-Host "Using Java $javaVersion from $javaHome"
}

if (-not (Test-Path -LiteralPath (Join-Path $serviceRoot "mvnw.cmd"))) {
    throw "Business API Maven Wrapper is missing"
}

Set-RepositoryJavaHome
Push-Location $serviceRoot
try {
    switch ($Action) {
        "test" { & ".\mvnw.cmd" "clean" "test" }
        "package" { & ".\mvnw.cmd" "clean" "package" }
        "run" { & ".\mvnw.cmd" "spring-boot:run" }
    }
    if ($LASTEXITCODE -ne 0) {
        throw "Business API $Action failed with exit code $LASTEXITCODE"
    }
}
finally {
    Pop-Location
}
