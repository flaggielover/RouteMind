[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$Casting = Join-Path $RepoRoot "infra/external-validation/vultr-tokyo-vm/signoz-casting.yaml"
$TempBase = [IO.Path]::GetFullPath([IO.Path]::GetTempPath())
$TempRoot = [IO.Path]::GetFullPath((Join-Path $TempBase ("routemind-foundry-" + [Guid]::NewGuid().ToString("N"))))
if (-not $TempRoot.StartsWith($TempBase, [StringComparison]::OrdinalIgnoreCase)) {
    throw "Foundry gate temporary path escaped the system temporary directory"
}

if ($IsWindows) {
    $Asset = "foundry_windows_amd64.tar.gz"
    $ExpectedSha256 = "625c7985b8ac6f3e4a99576c1dceaa4fa46fa4a54b2c53f515dff7f63da8dd4a"
    $ExecutablePattern = "*.exe"
}
elseif ($IsLinux) {
    $Asset = "foundry_linux_amd64.tar.gz"
    $ExpectedSha256 = "51f41204b8048cd1f7e278fb5d2ba5d82d2ee8fb619bfe9330e2f8ceffc0d886"
    $ExecutablePattern = "foundryctl"
}
else {
    throw "Foundry offline gate supports Windows and Linux AMD64 only"
}

try {
    New-Item -ItemType Directory -Path $TempRoot | Out-Null
    $Archive = Join-Path $TempRoot $Asset
    $Uri = "https://github.com/SigNoz/foundry/releases/download/v0.2.17/$Asset"
    Invoke-WebRequest -Uri $Uri -OutFile $Archive
    $ActualSha256 = (Get-FileHash -LiteralPath $Archive -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($ActualSha256 -ne $ExpectedSha256) {
        throw "Pinned Foundry asset digest changed"
    }
    & tar -xzf $Archive -C $TempRoot
    if ($LASTEXITCODE -ne 0) {
        throw "Foundry archive extraction failed"
    }
    $Foundry = Get-ChildItem -LiteralPath $TempRoot -Filter $ExecutablePattern -File -Recurse |
        Where-Object { $_.Name -match '^foundryctl(?:\.exe)?$' } |
        Select-Object -First 1
    if ($null -eq $Foundry) {
        throw "Foundry executable is absent from the pinned archive"
    }
    if ($IsLinux) {
        & chmod +x $Foundry.FullName
        if ($LASTEXITCODE -ne 0) { throw "Foundry executable permission update failed" }
    }

    $Work = Join-Path $TempRoot "work"
    New-Item -ItemType Directory -Path $Work | Out-Null
    $TemporaryCasting = Join-Path $Work "casting.yaml"
    Copy-Item -LiteralPath $Casting -Destination $TemporaryCasting
    if ($IsWindows) {
        $CastingText = Get-Content -LiteralPath $TemporaryCasting -Raw
        $CastingText = $CastingText.Replace(
            "target: deployment/compose.yaml",
            "target: 'deployment\compose.yaml'"
        )
        Set-Content -LiteralPath $TemporaryCasting -Value $CastingText -NoNewline
    }
    Push-Location $Work
    try {
        & $Foundry.FullName gauge -f casting.yaml --no-ledger --no-updater
        if ($LASTEXITCODE -ne 0) {
            throw "Pinned Foundry gauge failed"
        }
        & $Foundry.FullName forge -f casting.yaml --no-ledger --no-updater
        if ($LASTEXITCODE -ne 0) {
            throw "Pinned Foundry forge failed"
        }
        $Compose = Get-Content -LiteralPath "pours/deployment/compose.yaml" -Raw
        if ($Compose -match '(?m)^\s*image:\s*\S+:latest\s*$') {
            throw "Rendered SigNoz Compose contains a mutable latest tag"
        }
        if ($Compose -match '(?m)^\s*-\s*["'']?(?:0\.0\.0\.0:)?431[78]:431[78]["'']?\s*$') {
            throw "Rendered SigNoz Compose publishes OTLP on the host"
        }
        if ($Compose -notmatch '127\.0\.0\.1:8080:8080') {
            throw "Rendered SigNoz UI is not loopback-only"
        }
        foreach ($setting in @(
            "SIGNOZ_ANALYTICS_ENABLED=false",
            "SIGNOZ_STATSREPORTER_ENABLED=false",
            "SIGNOZ_STATSREPORTER_COLLECT_IDENTITIES=false"
        )) {
            if ($Compose -notmatch [regex]::Escape($setting)) {
                throw "Rendered SigNoz Compose is missing product-telemetry control $setting"
            }
        }
        foreach ($image in @(
            "signoz/signoz:v0.139.0",
            "signoz/signoz-otel-collector:v0.139.0",
            "postgres:16.10-alpine",
            "clickhouse/clickhouse-server:25.12.5",
            "clickhouse/clickhouse-keeper:25.12.5"
        )) {
            if ($Compose -notmatch [regex]::Escape($image)) {
                throw "Rendered SigNoz Compose is missing pinned image $image"
            }
        }
    }
    finally {
        Pop-Location
    }
    Write-Host "PASS: pinned SigNoz Foundry Compose render"
}
finally {
    if (Test-Path -LiteralPath $TempRoot) {
        $Resolved = [IO.Path]::GetFullPath($TempRoot)
        if (-not $Resolved.StartsWith($TempBase, [StringComparison]::OrdinalIgnoreCase)) {
            throw "Refusing to clean an unverified Foundry gate directory"
        }
        Remove-Item -LiteralPath $Resolved -Recurse -Force
    }
}
