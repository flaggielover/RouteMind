[CmdletBinding()]
param(
    [string] $OutputDirectory = "evidence/tests/tmp/R4-404",
    [switch] $SkipContainerResolution
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$output = [System.IO.Path]::GetFullPath((Join-Path $root $OutputDirectory))
$allowedRoot = [System.IO.Path]::GetFullPath((Join-Path $root "evidence/tests/tmp"))
if (-not $output.StartsWith($allowedRoot + [System.IO.Path]::DirectorySeparatorChar, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Supply-chain output must remain below evidence/tests/tmp"
}

$java = Get-Command java -ErrorAction SilentlyContinue
if (-not $java) { throw "Java 17 or newer is required" }
$previousErrorAction = $ErrorActionPreference
$ErrorActionPreference = "Continue"
$settings = & $java.Source -XshowSettings:properties -version 2>&1
$javaExitCode = $LASTEXITCODE
$ErrorActionPreference = $previousErrorAction
if ($javaExitCode -ne 0) { throw "Unable to inspect Java runtime" }
$homeLine = $settings | Where-Object { $_ -match '^\s*java\.home\s*=' } | Select-Object -First 1
$versionLine = $settings | Where-Object { $_ -match '^\s*java\.version\s*=' } | Select-Object -First 1
$javaHome = ($homeLine -replace '^\s*java\.home\s*=\s*', '').Trim()
$javaVersion = ($versionLine -replace '^\s*java\.version\s*=\s*', '').Trim()
$major = if ($javaVersion -match '^1\.(\d+)') { [int]$Matches[1] } elseif ($javaVersion -match '^(\d+)') { [int]$Matches[1] } else { 0 }
$javacName = if ($IsWindows -or [System.Environment]::OSVersion.Platform -eq [System.PlatformID]::Win32NT) { "javac.exe" } else { "javac" }
if ($major -lt 17 -or -not (Test-Path -LiteralPath (Join-Path $javaHome "bin/$javacName"))) {
    throw "A full JDK 17 or newer is required"
}
$env:JAVA_HOME = $javaHome

New-Item -ItemType Directory -Force -Path $output | Out-Null
$manifestDirectory = Join-Path $output "oci-manifests"
New-Item -ItemType Directory -Force -Path $manifestDirectory | Out-Null
$javaTree = Join-Path $output "maven-dependency-tree.txt"
$serviceRoot = Join-Path $root "services/business-api"
$wrapper = Join-Path $serviceRoot $(if ($IsWindows -or [System.Environment]::OSVersion.Platform -eq [System.PlatformID]::Win32NT) { "mvnw.cmd" } else { "mvnw" })
$mavenRepository = Join-Path $root ".tools/m2"

Push-Location $serviceRoot
try {
    & $wrapper "-Dmaven.repo.local=$mavenRepository" "org.apache.maven.plugins:maven-dependency-plugin:3.10.0:tree" "-DoutputFile=$javaTree" "-DoutputType=text"
    if ($LASTEXITCODE -ne 0) { throw "Maven dependency tree generation failed" }
}
finally {
    Pop-Location
}

if (-not $SkipContainerResolution) {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { throw "Docker buildx is required" }
    $references = python (Join-Path $PSScriptRoot "supply_chain_evidence.py") --root $root --list-images | ConvertFrom-Json
    if ($LASTEXITCODE -ne 0) { throw "Compose image enumeration failed" }
    foreach ($reference in $references) {
        $raw = docker buildx imagetools inspect $reference.image --raw
        if ($LASTEXITCODE -ne 0) { throw "OCI registry manifest resolution failed for $($reference.image)" }
        $manifestPath = Join-Path $manifestDirectory "$($reference.service).manifest.json"
        [System.IO.File]::WriteAllText($manifestPath, ($raw -join "`n"), [System.Text.UTF8Encoding]::new($false))
    }
}

$arguments = @(
    (Join-Path $PSScriptRoot "supply_chain_evidence.py"),
    "--root", $root,
    "--java-tree", $javaTree,
    "--container-manifest-dir", $manifestDirectory,
    "--output-dir", $output
)
if (-not $SkipContainerResolution) { $arguments += "--require-container-manifests" }
python @arguments
if ($LASTEXITCODE -ne 0) { throw "Supply-chain evidence generation failed" }

if (-not $SkipContainerResolution) {
    python (Join-Path $PSScriptRoot "supply_chain_evidence.py") --root $root --output-dir $output --validate
    if ($LASTEXITCODE -ne 0) { throw "Supply-chain evidence validation failed" }
}

Write-Host "PASS: dependency SBOM and content-addressed provenance evidence"
