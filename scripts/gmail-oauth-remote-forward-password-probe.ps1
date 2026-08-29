[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$serviceRoot = Join-Path $root "services/business-api"
$mavenRepository = Join-Path $root ".tools/m2"
$wrapper = Join-Path $serviceRoot "mvnw.cmd"

if ([Environment]::OSVersion.Platform -ne [System.PlatformID]::Win32NT) {
    throw "The password remote-forward probe must be launched on the Windows RouteMind host"
}

foreach ($name in @(
        "ROUTEMIND_GMAIL_OAUTH_MAC_KNOWN_HOSTS",
        "ROUTEMIND_GMAIL_OAUTH_MAC_PORT"
    )) {
    if ([string]::IsNullOrWhiteSpace([Environment]::GetEnvironmentVariable($name, "Process"))) {
        throw "Required password remote-forward configuration is missing: $name"
    }
}

if (-not (Test-Path -LiteralPath $wrapper -PathType Leaf)) {
    throw "Business API Maven Wrapper is missing"
}

# Maven uses JAVA_HOME rather than the first java.exe on PATH. Select an
# installed JDK 17+ without printing version output or any secret material.
$javaHomeCandidate = $env:JAVA_HOME
$javaMajor = 0
if ($javaHomeCandidate) {
    $javaExecutable = Join-Path $javaHomeCandidate "bin\java.exe"
    if (Test-Path -LiteralPath $javaExecutable -PathType Leaf) {
        $versionLine = (& $javaExecutable -version 2>&1 | Select-Object -First 1)
        if ($versionLine -match 'version "([0-9]+)(?:\.([0-9]+))?') {
            $javaMajor = [int]$matches[1]
            if ($javaMajor -eq 1 -and $matches[2]) { $javaMajor = [int]$matches[2] }
        }
    }
}
if ($javaMajor -lt 17) {
    $javaRoots = Join-Path ${env:ProgramFiles} "Java"
    $jdk = Get-ChildItem -LiteralPath $javaRoots -Directory -Filter "jdk-*" -ErrorAction SilentlyContinue |
        Where-Object {
            $version = 0
            if ($_.Name -match '^jdk-([0-9]+)') { $version = [int]$matches[1] }
            $version -ge 17 -and (Test-Path -LiteralPath (Join-Path $_.FullName "bin\java.exe") -PathType Leaf)
        } |
        Sort-Object Name -Descending |
        Select-Object -First 1
    if (-not $jdk) { throw "JDK 17 or newer is required for the password remote-forward probe" }
    $env:JAVA_HOME = $jdk.FullName
    $env:Path = (Join-Path $jdk.FullName "bin") + ";" + $env:Path
}

$env:ROUTEMIND_REPOSITORY_ROOT = $root
Push-Location $serviceRoot
try {
    $arguments = @(
        "-Dmaven.repo.local=$mavenRepository",
        "-Dspring-boot.run.main-class=com.routemind.business.infrastructure.notification.GmailOAuthPasswordRemoteForwardProbeCli",
        "spring-boot:run"
    )
    & $wrapper @arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Password remote-forward synthetic probe failed with exit code $LASTEXITCODE"
    }
}
finally {
    Pop-Location
}
