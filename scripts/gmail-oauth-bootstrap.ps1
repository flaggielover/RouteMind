[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$serviceRoot = Join-Path $root "services/business-api"
$mavenRepository = Join-Path $root ".tools/m2"
$onWindows = [System.Environment]::OSVersion.Platform -eq [System.PlatformID]::Win32NT
$wrapperName = if ($onWindows) { "mvnw.cmd" } else { "mvnw" }
$wrapper = Join-Path $serviceRoot $wrapperName

foreach ($name in @(
        "ROUTEMIND_GMAIL_OAUTH_CLIENT_FILE",
        "ROUTEMIND_GMAIL_TOKEN_STORE",
        "ROUTEMIND_GMAIL_OAUTH_USER_ID"
    )) {
    if ([string]::IsNullOrWhiteSpace([Environment]::GetEnvironmentVariable($name, "Process"))) {
        throw "Required OAuth bootstrap configuration is missing: $name"
    }
}

if (-not (Test-Path -LiteralPath $wrapper -PathType Leaf)) {
    throw "Business API Maven Wrapper is missing"
}

# The Java command performs canonical path, redirect, and Desktop credential-shape validation.
$env:ROUTEMIND_REPOSITORY_ROOT = $root
Push-Location $serviceRoot
try {
    $arguments = @(
        "-Dmaven.repo.local=$mavenRepository",
        "-Dspring-boot.run.main-class=com.routemind.business.infrastructure.notification.GmailOAuthBootstrapCli",
        "spring-boot:run"
    )
    if ($onWindows) {
        & $wrapper @arguments
    }
    else {
        if (-not (Get-Command bash -ErrorAction SilentlyContinue)) {
            throw "Bash is required to launch the Maven Wrapper on this platform"
        }
        & bash $wrapper @arguments
    }
    if ($LASTEXITCODE -ne 0) {
        throw "Gmail OAuth bootstrap failed with exit code $LASTEXITCODE"
    }
}
finally {
    Pop-Location
}
