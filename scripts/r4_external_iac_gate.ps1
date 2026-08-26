[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Root = Split-Path -Parent $PSScriptRoot
$IacRoot = Join-Path $Root "infra/external-validation/vultr-tokyo"
$DiagnosticIacRoot = Join-Path $Root "infra/external-validation/vultr-tokyo-diagnostic"
$tempBase = [IO.Path]::GetFullPath([IO.Path]::GetTempPath())
$tempRoot = [IO.Path]::GetFullPath((Join-Path $tempBase "routemind-r4-iac-$([guid]::NewGuid().ToString('N'))"))
if (-not $tempRoot.StartsWith($tempBase, [StringComparison]::OrdinalIgnoreCase)) {
    throw "Temporary IaC gate path escaped the system temporary directory"
}

function Invoke-Checked {
    param([Parameter(Mandatory)][string]$Command, [string[]]$Arguments = @())
    & $Command @Arguments
    if ($LASTEXITCODE -ne 0) { throw "$Command failed with exit code $LASTEXITCODE" }
}

foreach ($command in @("terraform", "helm")) {
    if (-not (Get-Command $command -ErrorAction SilentlyContinue)) {
        throw "R4 external IaC gate requires $command"
    }
}

$previousApiKey = $env:VULTR_API_KEY
$previousDataDir = $env:TF_DATA_DIR
try {
    New-Item -ItemType Directory -Path $tempRoot | Out-Null
    $env:VULTR_API_KEY = "offline-schema-validation-placeholder"
    $env:TF_DATA_DIR = Join-Path $tempRoot "terraform-data"
    Invoke-Checked "terraform" @("-chdir=$IacRoot", "fmt", "-check")
    Invoke-Checked "terraform" @("-chdir=$IacRoot", "init", "-backend=false", "-input=false", "-lockfile=readonly")
    Invoke-Checked "terraform" @("-chdir=$IacRoot", "validate")
    Invoke-Checked "terraform" @("-chdir=$DiagnosticIacRoot", "fmt", "-check")
    Invoke-Checked "terraform" @("-chdir=$DiagnosticIacRoot", "init", "-backend=false", "-input=false", "-lockfile=readonly")
    Invoke-Checked "terraform" @("-chdir=$DiagnosticIacRoot", "validate")

    Invoke-Checked "helm" @(
        "pull", "signoz", "--repo", "https://charts.signoz.io", "--version", "0.138.0", "--destination", $tempRoot
    )
    $chart = Join-Path $tempRoot "signoz-0.138.0.tgz"
    $digest = (Get-FileHash -LiteralPath $chart -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($digest -ne "b180a601b85b63b2e30ba953ea2242124a2c40f8f1cb66d8d948d71cd27d7418") {
        throw "Pinned SigNoz chart digest changed"
    }
    $values = Join-Path $IacRoot "signoz-values.yaml"
    Invoke-Checked "helm" @("lint", $chart, "--values", $values, "--set-string", "clickhouse.password=offline-validation-placeholder")
    $rendered = (& helm template routemind $chart --namespace routemind-observability --values $values --set-string clickhouse.password=offline-validation-placeholder) -join "`n"
    if ($LASTEXITCODE -ne 0) { throw "SigNoz template rendering failed" }
    if ($rendered -match '(?m)^\s*type:\s*LoadBalancer\s*$') { throw "Rendered SigNoz chart contains a public LoadBalancer" }
    foreach ($pattern in @(
        '(?s)name:\s+data.*?storage:\s+"3Gi"',
        '(?s)name:\s+signoz-db.*?storage:\s+2Gi',
        '(?s)name:\s+data-volumeclaim-template.*?storage:\s+30Gi',
        'client_ca_file:\s+/var/run/routemind-signoz-tls/ca.crt'
    )) {
        if ($rendered -notmatch $pattern) { throw "Rendered SigNoz boundary is absent: $pattern" }
    }

    $collector = Get-Content -LiteralPath (Join-Path $IacRoot "routemind-collector.yaml") -Raw
    if ([regex]::Matches($collector, '(?m)^\s*replicas:\s*2\s*$').Count -ne 1 -or
        [regex]::Matches($collector, '(?m)^\s*storage:\s*10Gi\s*$').Count -ne 1) {
        throw "RouteMind Collector replica or persistent-queue shape drifted"
    }
    $boundaries = Get-Content -LiteralPath (Join-Path $IacRoot "namespace-boundaries.yaml") -Raw
    if ($boundaries -notmatch '(?m)^\s*persistentvolumeclaims:\s*"5"\s*$' -or
        $boundaries -notmatch '(?m)^\s*requests.storage:\s*60Gi\s*$' -or
        $boundaries -notmatch '(?m)^\s*services.loadbalancers:\s*"0"\s*$') {
        throw "Namespace storage or public-service quota drifted"
    }
    $workload = Get-Content -LiteralPath (Join-Path $IacRoot "routemind-workload.yaml") -Raw
    $qualification = Get-Content -LiteralPath (Join-Path $IacRoot "workload-qualification.yaml") -Raw
    $queryJob = Get-Content -LiteralPath (Join-Path $IacRoot "clickhouse-query.yaml") -Raw
    $qualificationScript = Get-Content -LiteralPath (Join-Path $Root "scripts/r4_workload_qualification.py") -Raw
    foreach ($pattern in @(
        'name: routemind-app-tls',
        'name: routemind-runtime-secrets',
        '/api/v1/orders',
        'ROUTEMIND_TELEMETRY_ATTRIBUTION_KEY',
        'sourceRevision',
        'routemind-observability.svc.cluster.local:4318',
        'MANAGEMENT_TRACING_EXPORT_OTLP_ENABLED',
        'MANAGEMENT_OPENTELEMETRY_TRACING_EXPORT_OTLP_SSL_BUNDLE',
        'SPRING_SSL_BUNDLE_PEM_ROUTEMIND_KEYSTORE_PRIVATE_KEY',
        '--host, 0.0.0.0',
        'name: default-deny',
        'actualRouteMindWorkload'
    )) {
        if ($workload -notmatch [regex]::Escape($pattern) -and $qualification -notmatch [regex]::Escape($pattern) -and $qualificationScript -notmatch [regex]::Escape($pattern)) {
            throw "Actual RouteMind workload boundary is absent: $pattern"
        }
    }
    if ($workload -match 'validation-only-|change-me-local-only') { throw "Tracked workload contains a static credential" }
    if ($queryJob -notmatch 'secretKeyRef' -or $queryJob -match '(?m)^\s*value:\s*[^\s].*password') {
        throw "ClickHouse query credential is not injected from a Kubernetes Secret"
    }
    $diagnosticMain = Get-Content -LiteralPath (Join-Path $DiagnosticIacRoot "main.tf") -Raw
    $diagnosticCloudInit = Get-Content -LiteralPath (Join-Path $DiagnosticIacRoot "cloud-init.yaml.tftpl") -Raw
    foreach ($pattern in @(
        'node_quantity\s*=\s*1',
        'port\s*=\s*"6443"',
        'subnet_size\s*=\s*32',
        'vultr_instance\.recovery\.main_ip',
        'backups\s*=\s*"disabled"',
        'enable_ipv6\s*=\s*false'
    )) {
        if ($diagnosticMain -notmatch $pattern) { throw "VKE diagnostic IaC boundary is absent: $pattern" }
    }
    if ($diagnosticMain -match 'vultr_load_balancer|persistent_volume|block_storage|services\.loadbalancers') {
        throw "VKE diagnostic IaC contains a forbidden persistent or public resource"
    }
    if ($diagnosticCloudInit -match 'docker|git clone|customer|production') {
        throw "VKE diagnostic observer cloud-init contains an out-of-scope dependency"
    }
    Write-Host "PASS: R4 external Terraform and SigNoz Helm offline gate (5 PVC / 55 GiB / 0 LoadBalancer)"
}
finally {
    $env:VULTR_API_KEY = $previousApiKey
    $env:TF_DATA_DIR = $previousDataDir
    if (Test-Path -LiteralPath $tempRoot) {
        $resolved = [IO.Path]::GetFullPath($tempRoot)
        if (-not $resolved.StartsWith($tempBase, [StringComparison]::OrdinalIgnoreCase)) {
            throw "Refusing to clean an unverified temporary directory"
        }
        Remove-Item -LiteralPath $resolved -Recurse -Force
    }
}
