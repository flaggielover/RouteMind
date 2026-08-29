[CmdletBinding()]
param(
    [ValidateSet("test", "test-offline", "package", "run", "resilience", "ses-offline", "ses-context-audit")]
    [string] $Action = "test"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$serviceRoot = Join-Path $root "services/business-api"
$mavenRepository = Join-Path $root ".tools/m2"
$onWindows = [System.Environment]::OSVersion.Platform -eq [System.PlatformID]::Win32NT
$wrapperName = if ($onWindows) { "mvnw.cmd" } else { "mvnw" }
$wrapper = Join-Path $serviceRoot $wrapperName

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
    $javacName = if ($onWindows) { "javac.exe" } else { "javac" }
    $javac = Join-Path (Join-Path $javaHome "bin") $javacName
    if ($major -lt 17 -or -not (Test-Path -LiteralPath $javac)) {
        throw "A full JDK 17 or newer is required; found Java $javaVersion at $javaHome"
    }

    $env:JAVA_HOME = $javaHome
    Write-Host "Using Java $javaVersion from $javaHome"
}

function Invoke-Maven {
    param([Parameter(Mandatory)][string[]] $MavenArguments)

    if ($onWindows) {
        & $wrapper @MavenArguments
    }
    else {
        if (-not (Get-Command bash -ErrorAction SilentlyContinue)) {
            throw "Bash is required to launch the Maven Wrapper on this platform"
        }
        & bash $wrapper @MavenArguments
    }
}

if (-not (Test-Path -LiteralPath $wrapper)) {
    throw "Business API Maven Wrapper is missing"
}

Set-RepositoryJavaHome
Push-Location $serviceRoot
try {
    switch ($Action) {
        "test" { Invoke-Maven -MavenArguments @("-Dmaven.repo.local=$mavenRepository", "clean", "test") }
        "test-offline" { Invoke-Maven -MavenArguments @("--offline", "-Dmaven.repo.local=$mavenRepository", "clean", "test") }
        "package" { Invoke-Maven -MavenArguments @("-Dmaven.repo.local=$mavenRepository", "clean", "package") }
        "run" { Invoke-Maven -MavenArguments @("-Dmaven.repo.local=$mavenRepository", "spring-boot:run") }
        "resilience" { Invoke-Maven -MavenArguments @("-Dmaven.repo.local=$mavenRepository", "test", "-Dtest=BusinessApiApplicationTests") }
        "ses-offline" {
            $profile = [Environment]::GetEnvironmentVariable("AWS_PROFILE", "Process")
            $region = [Environment]::GetEnvironmentVariable("AWS_REGION", "Process")
            $defaultRegion = [Environment]::GetEnvironmentVariable("AWS_DEFAULT_REGION", "Process")
            if ($profile -ne "routemind-ses" -or $region -ne "ap-northeast-1" -or $defaultRegion -ne "ap-northeast-1") {
                throw "Offline SES construction requires the approved non-secret AWS profile and region configuration"
            }

            $previousMetadataDisabled = $env:AWS_EC2_METADATA_DISABLED
            $env:AWS_EC2_METADATA_DISABLED = "true"
            try {
                Invoke-Maven -MavenArguments @(
                    "-Dmaven.repo.local=$mavenRepository",
                    "clean",
                    "test",
                    "-Dtest=R4_422SesClientConstructionTests",
                    "-DfailIfNoTests=true",
                    "-Droutemind.ses.resolveCredentials=true"
                )
            }
            finally {
                $env:AWS_EC2_METADATA_DISABLED = $previousMetadataDisabled
            }

            if ($LASTEXITCODE -ne 0) {
                throw "Offline SES construction test failed"
            }
            Write-Host "AWS_SDK_DEFAULT_CREDENTIALS_PROVIDER=AVAILABLE"
            Write-Host "SES_CLIENT_CONSTRUCTION=AVAILABLE"
            Write-Host "AWS_NETWORK_REQUESTS=0"
            Write-Host "SEND_EMAIL_REQUESTS=0"
            Write-Host "COST_USD=0.00"
        }
        "ses-context-audit" {
            $senderPresent = -not [string]::IsNullOrWhiteSpace(
                [Environment]::GetEnvironmentVariable("ROUTEMIND_NOTIFICATION_SENDER", "Process")
            )
            $recipientPresent = -not [string]::IsNullOrWhiteSpace(
                [Environment]::GetEnvironmentVariable("ROUTEMIND_NOTIFICATION_SYNTHETIC_RECIPIENT", "Process")
            )
            if (-not $senderPresent -or -not $recipientPresent) {
                throw "Offline SES context audit requires both process-scoped notification endpoint variables"
            }

            Invoke-Maven -MavenArguments @(
                "--offline",
                "-Dmaven.repo.local=$mavenRepository",
                "test",
                "-Dtest=AwsSesRuntimeContextTests#currentProcessContextIsAuditedWithoutRevealingValues",
                "-DfailIfNoTests=true"
            )
            if ($LASTEXITCODE -ne 0) {
                throw "Offline SES context audit failed"
            }
            Write-Host "AWS_NETWORK_REQUESTS=0"
            Write-Host "SEND_EMAIL_REQUESTS=0"
            Write-Host "AWS_MUTATIONS=0"
        }
    }
    if ($LASTEXITCODE -ne 0) {
        throw "Business API $Action failed with exit code $LASTEXITCODE"
    }
}
finally {
    Pop-Location
}
