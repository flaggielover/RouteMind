[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$serviceRoot = Join-Path $root "services/business-api"
$mavenRepository = Join-Path $root ".tools/m2"
$wrapper = Join-Path $serviceRoot "mvnw.cmd"

if ([Environment]::OSVersion.Platform -ne [System.PlatformID]::Win32NT) {
    throw "The ssh -R bootstrap must be launched on the Windows RouteMind host"
}

foreach ($name in @(
        "ROUTEMIND_GMAIL_OAUTH_CLIENT_FILE",
        "ROUTEMIND_GMAIL_TOKEN_STORE",
        "ROUTEMIND_GMAIL_OAUTH_USER_ID",
        "ROUTEMIND_GMAIL_OAUTH_MAC_SSH_KEY_PATH",
        "ROUTEMIND_GMAIL_OAUTH_MAC_KNOWN_HOSTS",
        "ROUTEMIND_GMAIL_OAUTH_MAC_PORT"
    )) {
    if ([string]::IsNullOrWhiteSpace([Environment]::GetEnvironmentVariable($name, "Process"))) {
        throw "Required cross-device OAuth configuration is missing: $name"
    }
}

if (-not (Test-Path -LiteralPath $wrapper -PathType Leaf)) {
    throw "Business API Maven Wrapper is missing"
}

# Java owns canonical path, scope, and Desktop credential-shape validation. The
# remote CLI owns only the explicit SSH tunnel and the single token exchange.
$env:ROUTEMIND_REPOSITORY_ROOT = $root
Push-Location $serviceRoot
try {
    $arguments = @(
        "-Dmaven.repo.local=$mavenRepository",
        "-Dspring-boot.run.main-class=com.routemind.business.infrastructure.notification.GmailOAuthRemoteBootstrapCli",
        "spring-boot:run"
    )
    & $wrapper @arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Gmail cross-device OAuth bootstrap failed with exit code $LASTEXITCODE"
    }
}
finally {
    Pop-Location
}
