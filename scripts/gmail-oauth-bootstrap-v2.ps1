[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$serviceRoot = Join-Path $root "services/business-api"
$mavenRepository = Join-Path $root ".tools/m2"
$wrapper = Join-Path $serviceRoot "mvnw.cmd"

if ([Environment]::OSVersion.Platform -ne [System.PlatformID]::Win32NT) {
    throw "Gmail OAuth bootstrap V2 requires the Windows RouteMind host"
}

foreach ($name in @(
        "ROUTEMIND_GMAIL_OAUTH_CLIENT_FILE",
        "ROUTEMIND_GMAIL_TOKEN_STORE",
        "ROUTEMIND_GMAIL_OAUTH_USER_ID",
        "ROUTEMIND_GMAIL_OAUTH_MAC_KNOWN_HOSTS",
        "ROUTEMIND_GMAIL_OAUTH_MAC_PORT"
    )) {
    if ([string]::IsNullOrWhiteSpace([Environment]::GetEnvironmentVariable($name, "Process"))) {
        throw "Required Gmail OAuth V2 configuration is missing: $name"
    }
}

if (-not (Test-Path -LiteralPath $wrapper -PathType Leaf)) {
    throw "Business API Maven Wrapper is missing"
}

# The V2 command never starts ssh.exe. It only starts the loopback listener,
# prints a sanitized manual command, and waits for operator preflight.
$env:ROUTEMIND_REPOSITORY_ROOT = $root
Push-Location $serviceRoot
try {
    $arguments = @(
        "-Dmaven.repo.local=$mavenRepository",
        "-Dspring-boot.run.main-class=com.routemind.business.infrastructure.notification.GmailOAuthBootstrapV2Cli",
        "spring-boot:run"
    )
    & $wrapper @arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Gmail OAuth bootstrap V2 failed with exit code $LASTEXITCODE"
    }
}
finally {
    Pop-Location
}
