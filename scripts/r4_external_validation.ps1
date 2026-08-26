[CmdletBinding()]
param(
    [ValidateSet("OfflinePreflight", "LivePreflight", "Provision", "Deploy", "Validate", "Teardown", "Full")]
    [string]$Action = "OfflinePreflight",
    [string]$ExecutionId,
    [switch]$AcknowledgeExternalExecution
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Root = Split-Path -Parent $PSScriptRoot
$IacRoot = Join-Path $Root "infra/external-validation/vultr-tokyo"
$ContractScript = Join-Path $PSScriptRoot "r4_external_validation.py"
$EvidenceAssembler = Join-Path $PSScriptRoot "r4_external_evidence.py"
$PathSafetyScript = Join-Path $PSScriptRoot "path_safety.py"
$ContractPath = Join-Path $Root "contracts/external-validation/r4-vultr-tokyo-external-validation-v1.json"
$CollectorConfig = Join-Path $Root "infra/observability/otel-collector.yaml"
$ProbeScript = Join-Path $PSScriptRoot "r4_telemetry_probe.py"
$WorkloadScript = Join-Path $PSScriptRoot "r4_workload_qualification.py"
$DataRoot = if ($env:ROUTEMIND_DATA_ROOT) {
    [IO.Path]::GetFullPath($env:ROUTEMIND_DATA_ROOT)
} else {
    [IO.Path]::GetFullPath((Join-Path (Split-Path -Parent $Root) "RouteMind-Data"))
}
$dataRootRelative = [IO.Path]::GetRelativePath($Root, $DataRoot)
if (-not $dataRootRelative.StartsWith("..") -and -not [IO.Path]::IsPathRooted($dataRootRelative)) {
    throw "ROUTEMIND_DATA_ROOT must remain outside the repository"
}

function Invoke-Native {
    param([Parameter(Mandatory)][string]$Command, [string[]]$Arguments = @())
    & $Command @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Command failed with exit code $LASTEXITCODE"
    }
}

function Invoke-NativeCapture {
    param([Parameter(Mandatory)][string]$Command, [string[]]$Arguments = @())
    $output = & $Command @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Command failed with exit code $LASTEXITCODE"
    }
    return ($output -join "`n")
}

function Require-Command {
    param([Parameter(Mandatory)][string]$Name)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required execution tool is missing: $Name"
    }
}

function New-RandomSecret {
    return [Convert]::ToHexString(
        [Security.Cryptography.RandomNumberGenerator]::GetBytes(32)
    ).ToLowerInvariant()
}

function Get-ContractSummary {
    $raw = Invoke-NativeCapture "python" @($ContractScript)
    return $raw | ConvertFrom-Json
}

function Assert-ExternalGate {
    param([Parameter(Mandatory)]$Summary)
    if (-not $AcknowledgeExternalExecution) {
        throw "Mutating or credentialed action requires -AcknowledgeExternalExecution"
    }
    if ($env:ROUTEMIND_EXTERNAL_EXECUTION_APPROVAL_DIGEST -ne $Summary.contractDigest) {
        throw "The external-execution approval digest is absent or does not match the frozen contract"
    }
    foreach ($name in @("VULTR_API_KEY", "ROUTEMIND_SSH_PRIVATE_KEY_PATH", "ROUTEMIND_VULTR_SSH_KEY_ID", "ROUTEMIND_OPERATOR_CIDR")) {
        if ([string]::IsNullOrWhiteSpace([Environment]::GetEnvironmentVariable($name))) {
            throw "Required external-execution configuration is absent: $name"
        }
    }
    Invoke-Native "python" @(
        $PathSafetyScript,
        "--root", $Root,
        "--candidate-env", "ROUTEMIND_SSH_PRIVATE_KEY_PATH"
    )
}

function New-ExecutionId {
    $revision = (Invoke-NativeCapture "git" @("rev-parse", "--short=10", "HEAD")).Trim()
    $stamp = [DateTime]::UtcNow.ToString("yyyyMMdd'T'HHmmss'Z'").ToLowerInvariant()
    return "r4-ext-$stamp-$revision"
}

function Get-ExecutionPaths {
    param([Parameter(Mandatory)][string]$Id)
    if ($Id -notmatch '^r4-ext-[0-9]{8}t[0-9]{6}z-[0-9a-f]{7,12}$') {
        throw "ExecutionId does not match the frozen bounded identity format"
    }
    $rootPath = [IO.Path]::GetFullPath((Join-Path $DataRoot "external-validation/$Id"))
    $relative = [IO.Path]::GetRelativePath($DataRoot, $rootPath)
    if ($relative.StartsWith("..") -or [IO.Path]::IsPathRooted($relative)) {
        throw "Execution state path escaped ROUTEMIND_DATA_ROOT"
    }
    return [pscustomobject]@{
        Root = $rootPath
        Evidence = Join-Path $rootPath "sanitized-evidence"
        Secrets = Join-Path $rootPath "secrets"
        TerraformData = Join-Path $rootPath "terraform-data"
        TerraformState = Join-Path $rootPath "terraform.tfstate"
        Vars = Join-Path $rootPath "execution.auto.tfvars.json"
        Quote = Join-Path $rootPath "authenticated-quote.json"
        Kubeconfig = Join-Path $rootPath "kubeconfig.yaml"
        StartedAt = Join-Path $rootPath "execution-started-at.txt"
        Lifecycle = Join-Path $rootPath "execution-lifecycle.json"
        FinalReport = Join-Path $rootPath "r4-external-validation-evidence.json"
        TraceId = Join-Path $rootPath "validated-trace-id.txt"
    }
}

function Initialize-StateDirectory {
    param([Parameter(Mandatory)]$Paths)
    foreach ($path in @($Paths.Root, $Paths.Evidence, $Paths.Secrets, $Paths.TerraformData)) {
        New-Item -ItemType Directory -Path $path -Force | Out-Null
    }
    if (-not (Test-Path -LiteralPath $Paths.StartedAt)) {
        [DateTime]::UtcNow.ToString("yyyy-MM-dd'T'HH:mm:ss'Z'") | Set-Content -LiteralPath $Paths.StartedAt -Encoding ascii -NoNewline
    }
    if ($IsWindows -and (Get-Command icacls -ErrorAction SilentlyContinue)) {
        & icacls $Paths.Root /inheritance:r /grant:r "${env:USERNAME}:(OI)(CI)F" | Out-Null
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to restrict the execution state directory ACL"
        }
    } elseif (Get-Command chmod -ErrorAction SilentlyContinue) {
        Invoke-Native "chmod" @("700", $Paths.Root, $Paths.Secrets, $Paths.TerraformData)
    }
}

function Invoke-OfflinePreflight {
    $summary = Get-ContractSummary
    Invoke-Native "python" @("-m", "py_compile", $ContractScript, $EvidenceAssembler, $PathSafetyScript, $ProbeScript, $WorkloadScript)
    Invoke-Native "python" @(Join-Path $PSScriptRoot "path_safety_test.py")
    Invoke-Native "python" @(Join-Path $PSScriptRoot "r4_external_validation_test.py")
    Invoke-Native "python" @(Join-Path $PSScriptRoot "telemetry_export_contract.py")
    Invoke-Native "python" @(Join-Path $PSScriptRoot "telemetry_export_contract_test.py")
    Invoke-Native "python" @(Join-Path $PSScriptRoot "disaster_recovery_test.py")
    Invoke-Native "python" @(Join-Path $PSScriptRoot "security_gate.py")
    [pscustomobject]@{
        valid = $true
        action = "OfflinePreflight"
        contractDigest = $summary.contractDigest
        backend = $summary.backend
        provider = $summary.provider
        region = $summary.region
        resourceCreationAuthorized = $summary.resourceCreationAuthorized
        externalValidationExecuted = $summary.externalValidationExecuted
    } | ConvertTo-Json -Compress
}

function Invoke-VultrGet {
    param([Parameter(Mandatory)][string]$Path)
    $headers = @{ Authorization = "Bearer $env:VULTR_API_KEY" }
    return Invoke-RestMethod -Method Get -Uri "https://api.vultr.com/v2$Path" -Headers $headers -TimeoutSec 30
}

function Invoke-LivePreflight {
    param([Parameter(Mandatory)]$Summary, [Parameter(Mandatory)]$Paths)
    Assert-ExternalGate $Summary
    Initialize-StateDirectory $Paths
    $trackedChanges = Invoke-NativeCapture "git" @("status", "--porcelain", "--untracked-files=no")
    if (-not [string]::IsNullOrWhiteSpace($trackedChanges)) {
        throw "External execution requires a clean tracked working tree"
    }
    $revision = (Invoke-NativeCapture "git" @("rev-parse", "HEAD")).Trim()
    $trackedRevision = (Invoke-NativeCapture "git" @("rev-parse", "origin/main")).Trim()
    $remoteLine = (Invoke-NativeCapture "git" @("ls-remote", "origin", "refs/heads/main")).Trim()
    if ($remoteLine -notmatch '^([0-9a-f]{40})\s+refs/heads/main$') {
        throw "External execution could not resolve the remote main revision"
    }
    if ($revision -ne $trackedRevision -or $revision -ne $Matches[1]) {
        throw "External execution requires HEAD == origin/main == remote main"
    }
    $null = Invoke-VultrGet "/account"
    $regions = Invoke-VultrGet "/regions?per_page=500"
    $region = @($regions.regions) | Where-Object { $_.id -eq "nrt" } | Select-Object -First 1
    if (-not $region -or $region.city -ne "Tokyo" -or $region.country -ne "JP" -or "kubernetes" -notin @($region.options)) {
        throw "Authenticated provider evidence did not prove the Vultr Tokyo VKE target"
    }
    $availability = Invoke-VultrGet "/regions/nrt/availability"
    $availablePlans = @($availability.available_plans)
    foreach ($planId in @("vhp-4c-8gb-amd", "vhp-2c-4gb-amd")) {
        if ($planId -notin $availablePlans) {
            throw "Required plan is not available in nrt: $planId"
        }
    }
    $plans = Invoke-VultrGet "/plans?per_page=500"
    $worker = @($plans.plans) | Where-Object { $_.id -eq "vhp-4c-8gb-amd" } | Select-Object -First 1
    $recovery = @($plans.plans) | Where-Object { $_.id -eq "vhp-2c-4gb-amd" } | Select-Object -First 1
    if (-not $worker -or -not $recovery) {
        throw "Authenticated plan pricing is incomplete"
    }
    $versions = Invoke-VultrGet "/kubernetes/versions"
    $versionIds = @($versions.versions) | ForEach-Object {
        if ($_ -is [string]) { $_ } elseif ($_.version) { $_.version } elseif ($_.id) { $_.id }
    } | Where-Object { $_ -match '^v[0-9]+\.[0-9]+\.[0-9]+\+[0-9]+$' }
    $vkeVersion = $versionIds | Select-Object -First 1
    if (-not $vkeVersion) {
        throw "No exact supported VKE version was returned"
    }
    $operatingSystems = Invoke-VultrGet "/os?per_page=500"
    $os = @($operatingSystems.os) | Where-Object {
        $_.name -match 'Ubuntu 24\.04.*x64' -and ($_.arch -eq "x64" -or -not $_.arch)
    } | Select-Object -First 1
    if (-not $os) {
        throw "Authenticated catalog did not return Ubuntu 24.04 x64"
    }
    $computeCents = [Math]::Ceiling((3 * [double]$worker.hourly_cost + [double]$recovery.hourly_cost) * 8 * 100)
    $storageCents = [Math]::Ceiling((60 * 0.10 / 730) * 8 * 100)
    $upperBoundCents = [int]($computeCents + $storageCents + 200)
    if ($upperBoundCents -gt [int]$Summary.executionAuthorizationCeilingUsdCents) {
        throw "Authenticated bounded quote exceeds the frozen USD 15 ceiling"
    }
    $expiresAt = [DateTime]::UtcNow.AddHours(8).ToString("yyyy-MM-dd'T'HH:mm:ss'Z'")
    $quote = [ordered]@{
        schemaVersion = 1
        source = "authenticated_vultr_api"
        observedAt = [DateTime]::UtcNow.ToString("yyyy-MM-dd'T'HH:mm:ss'Z'")
        provider = "Vultr"
        region = "nrt"
        city = "Tokyo"
        country = "JP"
        executionId = $ExecutionId
        vkeVersion = $vkeVersion
        recoveryOsId = [int]$os.id
        workerPlan = [ordered]@{ id = $worker.id; count = 3; hourlyUsd = [double]$worker.hourly_cost }
        recoveryPlan = [ordered]@{ id = $recovery.id; count = 1; hourlyUsd = [double]$recovery.hourly_cost }
        maximumStorageGiB = 60
        maximumRuntimeHours = 8
        upperBoundUsdCents = $upperBoundCents
        approvedCeilingUsdCents = [int]$Summary.executionAuthorizationCeilingUsdCents
        withinApprovedCeiling = $true
    }
    $quote | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $Paths.Quote -Encoding utf8
    [ordered]@{
        execution_id = $ExecutionId
        source_revision = $revision
        expires_at = $expiresAt
        vke_version = $vkeVersion
        recovery_os_id = [int]$os.id
        ssh_key_id = $env:ROUTEMIND_VULTR_SSH_KEY_ID
        operator_cidr = $env:ROUTEMIND_OPERATOR_CIDR
    } | ConvertTo-Json | Set-Content -LiteralPath $Paths.Vars -Encoding utf8
    return $quote
}

function Set-TerraformEnvironment {
    param([Parameter(Mandatory)]$Paths)
    $env:TF_DATA_DIR = $Paths.TerraformData
    $env:TF_IN_AUTOMATION = "1"
    $env:TF_INPUT = "0"
}

function Invoke-Provision {
    param([Parameter(Mandatory)]$Summary, [Parameter(Mandatory)]$Paths)
    foreach ($tool in @("terraform", "kubectl", "helm", "openssl", "ssh", "scp")) { Require-Command $tool }
    if (-not (Test-Path -LiteralPath $Paths.Quote) -or -not (Test-Path -LiteralPath $Paths.Vars)) {
        $null = Invoke-LivePreflight $Summary $Paths
    }
    Set-TerraformEnvironment $Paths
    Invoke-Native "terraform" @("-chdir=$IacRoot", "fmt", "-check")
    Invoke-Native "terraform" @("-chdir=$IacRoot", "init", "-reconfigure", "-backend-config=path=$($Paths.TerraformState)")
    $planPath = Join-Path $Paths.Root "provision.tfplan"
    $planJson = Join-Path $Paths.Root "provision-plan.json"
    Invoke-Native "terraform" @("-chdir=$IacRoot", "plan", "-out=$planPath", "-var-file=$($Paths.Vars)")
    $shown = Invoke-NativeCapture "terraform" @("-chdir=$IacRoot", "show", "-json", $planPath)
    $shown | Set-Content -LiteralPath $planJson -Encoding utf8
    Invoke-Native "python" @($ContractScript, "--terraform-plan", $planJson)
    Invoke-Native "terraform" @("-chdir=$IacRoot", "apply", "-auto-approve", $planPath)
    $inventory = Invoke-NativeCapture "terraform" @("-chdir=$IacRoot", "output", "-json", "validation_inventory")
    $inventory | Set-Content -LiteralPath (Join-Path $Paths.Evidence "terraform-resource-output.json") -Encoding utf8
    $kubeConfigBase64 = (Invoke-NativeCapture "terraform" @("-chdir=$IacRoot", "output", "-raw", "vke_kube_config")).Trim()
    [IO.File]::WriteAllBytes($Paths.Kubeconfig, [Convert]::FromBase64String($kubeConfigBase64))
    $env:KUBECONFIG = $Paths.Kubeconfig
    for ($attempt = 0; $attempt -lt 60; $attempt++) {
        & kubectl get nodes | Out-Null
        if ($LASTEXITCODE -eq 0) { return }
        Start-Sleep -Seconds 10
    }
    throw "VKE nodes did not become reachable within the bounded wait"
}

function New-TlsMaterial {
    param([Parameter(Mandatory)]$Paths)
    $certRoot = $Paths.Secrets
    foreach ($name in @("telemetry-attribution-key", "postgres-password", "rabbitmq-password", "redis-password")) {
        $value = New-RandomSecret
        $value | Set-Content -LiteralPath (Join-Path $certRoot $name) -Encoding ascii -NoNewline
    }
    $caKey = Join-Path $certRoot "ca.key"
    $caCert = Join-Path $certRoot "ca.crt"
    Invoke-Native "openssl" @("genrsa", "-out", $caKey, "3072")
    Invoke-Native "openssl" @("req", "-x509", "-new", "-nodes", "-key", $caKey, "-sha256", "-days", "1", "-subj", "/CN=RouteMind-R4-External-Validation-CA", "-out", $caCert)
    $identities = @(
        @{ Name = "signoz"; CommonName = "routemind-signoz-otel-collector.routemind-observability.svc.cluster.local"; Usage = "serverAuth" },
        @{ Name = "receiver"; CommonName = "routemind-otel-collector.routemind-observability.svc.cluster.local"; Usage = "serverAuth" },
        @{ Name = "exporter"; CommonName = "routemind-collector-client"; Usage = "clientAuth" },
        @{ Name = "probe"; CommonName = "routemind-validation-probe"; Usage = "clientAuth" }
    )
    $first = $true
    foreach ($identity in $identities) {
        $key = Join-Path $certRoot "$($identity.Name).key"
        $csr = Join-Path $certRoot "$($identity.Name).csr"
        $cert = Join-Path $certRoot "$($identity.Name).crt"
        $extension = Join-Path $certRoot "$($identity.Name).ext"
        $extensionLines = @("extendedKeyUsage=$($identity.Usage)")
        if ($identity.Usage -eq "serverAuth") { $extensionLines += "subjectAltName=DNS:$($identity.CommonName)" }
        $extensionLines | Set-Content -LiteralPath $extension -Encoding ascii
        Invoke-Native "openssl" @("req", "-new", "-newkey", "rsa:2048", "-nodes", "-keyout", $key, "-out", $csr, "-subj", "/CN=$($identity.CommonName)")
        $serialArguments = if ($first) { @("-CAcreateserial") } else { @("-CAserial", (Join-Path $certRoot "ca.srl")) }
        Invoke-Native "openssl" (@("x509", "-req", "-in", $csr, "-CA", $caCert, "-CAkey", $caKey) + $serialArguments + @("-out", $cert, "-days", "1", "-sha256", "-extfile", $extension))
        $first = $false
    }
}

function Apply-SecretFromFiles {
    param([string]$Namespace, [string]$Name, [hashtable]$Files)
    $arguments = @("create", "secret", "generic", $Name, "-n", $Namespace, "--dry-run=client", "-o", "json")
    foreach ($key in ($Files.Keys | Sort-Object)) { $arguments += "--from-file=$key=$($Files[$key])" }
    $secretJson = Invoke-NativeCapture "kubectl" $arguments
    $secretJson | & kubectl apply -f - | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Failed to apply Kubernetes Secret $Namespace/$Name" }
}

function Resolve-DeploymentArtifacts {
    param([Parameter(Mandatory)]$Paths, [Parameter(Mandatory)][string]$ChartPath, [Parameter(Mandatory)][string]$SecretValues)
    Require-Command "docker"
    $rendered = Invoke-NativeCapture "helm" @(
        "template", "routemind", $ChartPath,
        "--namespace", "routemind-observability",
        "--values", (Join-Path $IacRoot "signoz-values.yaml"),
        "--values", $SecretValues
    )
    $manifestText = @(
        $rendered,
        (Get-Content -LiteralPath (Join-Path $IacRoot "routemind-collector.yaml") -Raw),
        (Get-Content -LiteralPath (Join-Path $IacRoot "telemetry-probe.yaml") -Raw),
        (Get-Content -LiteralPath (Join-Path $IacRoot "routemind-workload.yaml") -Raw),
        (Get-Content -LiteralPath (Join-Path $IacRoot "workload-qualification.yaml") -Raw),
        (Get-Content -LiteralPath (Join-Path $IacRoot "clickhouse-query.yaml") -Raw)
    ) -join "`n"
    $images = [regex]::Matches($manifestText, '(?m)^\s*image:\s*["'']?([^\s"'']+)') |
        ForEach-Object { $_.Groups[1].Value } | Sort-Object -Unique
    if ($images.Count -lt 4) { throw "Rendered deployment image inventory is unexpectedly small" }
    $resolved = [System.Collections.Generic.List[object]]::new()
    foreach ($image in $images) {
        if ($image -match '@sha256:([0-9a-f]{64})$') {
            $digest = "sha256:$($Matches[1])"
        } else {
            $manifest = Invoke-NativeCapture "docker" @(
                "buildx", "imagetools", "inspect", $image, "--format", "{{json .Manifest}}"
            ) | ConvertFrom-Json
            $digest = [string]$manifest.digest
        }
        if ($digest -notmatch '^sha256:[0-9a-f]{64}$') { throw "Image digest resolution failed: $image" }
        $resolved.Add([ordered]@{ image = $image; digest = $digest })
    }
    $result = [ordered]@{
        resolvedAt = [DateTime]::UtcNow.ToString("yyyy-MM-dd'T'HH:mm:ss'Z'")
        chart = [ordered]@{
            name = "signoz"; version = "0.138.0"
            sha256 = (Get-FileHash -LiteralPath $ChartPath -Algorithm SHA256).Hash.ToLowerInvariant()
        }
        images = $resolved
    }
    $result | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $Paths.Root "artifact-digest-manifest.json") -Encoding utf8
    return $result
}

function Write-AuthenticatedResourceManifest {
    param([Parameter(Mandatory)]$Paths)
    $terraformInventory = Get-Content -LiteralPath (Join-Path $Paths.Evidence "terraform-resource-output.json") -Raw | ConvertFrom-Json
    $vke = (Invoke-VultrGet "/kubernetes/clusters/$($terraformInventory.vke_id)").vke_cluster
    $instance = (Invoke-VultrGet "/instances/$($terraformInventory.recovery_id)").instance
    if ($vke.region -ne "nrt" -or $instance.region -ne "nrt") { throw "Credentialed resource identity escaped nrt" }
    $pvs = Invoke-NativeCapture "kubectl" @("get", "pv", "-o", "json") | ConvertFrom-Json
    $volumeIds = @($pvs.items) | Where-Object {
        $_.spec.claimRef.namespace -eq "routemind-observability"
    } | ForEach-Object { $_.spec.csi.volumeHandle } | Where-Object { $_ } | Sort-Object -Unique
    if ($volumeIds.Count -ne 5) { throw "VKE CSI volume inventory differs from the approved five-volume bound" }
    $boundPvs = @($pvs.items) | Where-Object { $_.spec.claimRef.namespace -eq "routemind-observability" }
    if (@($boundPvs | Where-Object { $_.spec.persistentVolumeReclaimPolicy -ne "Delete" }).Count -ne 0) {
        throw "A validation persistent volume is not configured for deletion"
    }
    $blocks = foreach ($volumeId in $volumeIds) {
        $block = (Invoke-VultrGet "/blocks/$volumeId").block
        if ($block.region -ne "nrt") { throw "VKE CSI block storage escaped nrt" }
        $block
    }
    $created = {
        param($resource)
        $value = [string]$resource.date_created
        if ($value -notmatch '^\d{4}-\d{2}-\d{2}T') { throw "Provider resource lacks a creation timestamp" }
        return ([DateTimeOffset]::Parse($value)).UtcDateTime.ToString("yyyy-MM-dd'T'HH:mm:ss'Z'")
    }
    $resources = [System.Collections.Generic.List[object]]::new()
    $resources.Add([ordered]@{
        type = "Vultr Kubernetes Engine"; providerId = [string]$vke.id; region = "nrt"
        createdAt = (& $created $vke); deletedAt = $null; cleanupVerified = $false
    })
    $resources.Add([ordered]@{
        type = "Vultr Cloud Compute"; providerId = [string]$instance.id; region = "nrt"
        createdAt = (& $created $instance); deletedAt = $null; cleanupVerified = $false
    })
    foreach ($block in $blocks) {
        $resources.Add([ordered]@{
            type = "Vultr Block Storage"; providerId = [string]$block.id; region = "nrt"
            createdAt = (& $created $block); deletedAt = $null; cleanupVerified = $false
        })
    }
    $manifest = [ordered]@{
        schemaVersion = 1; identitySource = "authenticated_vultr_api_and_vke_csi"
        observedAt = [DateTime]::UtcNow.ToString("yyyy-MM-dd'T'HH:mm:ss'Z'")
        provider = "Vultr"; region = "nrt"; executionId = $ExecutionId
        resources = $resources
        controlResourceIds = [ordered]@{ firewallGroup = [string]$terraformInventory.firewall_group_id }
        sourceRevision = [string]$terraformInventory.source_revision
    }
    $manifest | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $Paths.Evidence "authenticated-resource-manifest.json") -Encoding utf8
}

function Invoke-Deploy {
    param([Parameter(Mandatory)]$Summary, [Parameter(Mandatory)]$Paths)
    Assert-ExternalGate $Summary
    foreach ($tool in @("kubectl", "helm", "openssl", "docker")) { Require-Command $tool }
    if (-not (Test-Path -LiteralPath $Paths.Kubeconfig)) { throw "Provisioned kubeconfig is absent" }
    $env:KUBECONFIG = $Paths.Kubeconfig
    New-TlsMaterial $Paths
    $storageClass = Invoke-NativeCapture "kubectl" @("get", "storageclass", "vultr-block-storage", "-o", "json") | ConvertFrom-Json
    if ($storageClass.reclaimPolicy -ne "Delete" -or $storageClass.volumeBindingMode -notin @("WaitForFirstConsumer", "Immediate")) {
        throw "VKE storage class is not safely reclaimable for bounded validation"
    }
    Invoke-Native "kubectl" @("apply", "-f", (Join-Path $IacRoot "namespace-boundaries.yaml"))
    $validationNamespace = Invoke-NativeCapture "kubectl" @("create", "namespace", "routemind-validation", "--dry-run=client", "-o", "json")
    $validationNamespace | & kubectl apply -f - | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Failed to create the isolated validation namespace" }
    Invoke-Native "kubectl" @("label", "namespace", "routemind-validation", "routemind.io/external-validation-client=true", "routemind.io/data-residency=tokyo", "--overwrite")
    $appNamespace = Invoke-NativeCapture "kubectl" @("create", "namespace", "routemind-app", "--dry-run=client", "-o", "json")
    $appNamespace | & kubectl apply -f - | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Failed to create the RouteMind workload namespace" }
    Invoke-Native "kubectl" @("label", "namespace", "routemind-app", "routemind.io/external-validation=true", "routemind.io/data-residency=tokyo", "--overwrite")
    $ca = Join-Path $Paths.Secrets "ca.crt"
    Apply-SecretFromFiles "routemind-observability" "routemind-signoz-tls" @{
        "ca.crt" = $ca; "tls.crt" = (Join-Path $Paths.Secrets "signoz.crt"); "tls.key" = (Join-Path $Paths.Secrets "signoz.key")
    }
    Apply-SecretFromFiles "routemind-observability" "routemind-otel-collector-tls" @{
        "ca.crt" = $ca; "receiver.crt" = (Join-Path $Paths.Secrets "receiver.crt"); "receiver.key" = (Join-Path $Paths.Secrets "receiver.key"); "exporter.crt" = (Join-Path $Paths.Secrets "exporter.crt"); "exporter.key" = (Join-Path $Paths.Secrets "exporter.key")
    }
    Apply-SecretFromFiles "routemind-validation" "routemind-telemetry-probe-tls" @{
        "ca.crt" = $ca; "tls.crt" = (Join-Path $Paths.Secrets "probe.crt"); "tls.key" = (Join-Path $Paths.Secrets "probe.key")
    }
    Apply-SecretFromFiles "routemind-app" "routemind-app-tls" @{
        "ca.crt" = $ca; "tls.crt" = (Join-Path $Paths.Secrets "exporter.crt"); "tls.key" = (Join-Path $Paths.Secrets "exporter.key")
    }
    Apply-SecretFromFiles "routemind-app" "routemind-runtime-secrets" @{
        "ROUTEMIND_TELEMETRY_ATTRIBUTION_KEY" = (Join-Path $Paths.Secrets "telemetry-attribution-key")
        "POSTGRES_PASSWORD" = (Join-Path $Paths.Secrets "postgres-password")
        "RABBITMQ_DEFAULT_PASS" = (Join-Path $Paths.Secrets "rabbitmq-password")
        "REDIS_PASSWORD" = (Join-Path $Paths.Secrets "redis-password")
    }
    $chartPath = Join-Path $Paths.Root "signoz-0.138.0.tgz"
    Invoke-Native "helm" @("pull", "signoz", "--repo", "https://charts.signoz.io", "--version", "0.138.0", "--destination", $Paths.Root)
    $chartDigest = (Get-FileHash -LiteralPath $chartPath -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($chartDigest -ne "b180a601b85b63b2e30ba953ea2242124a2c40f8f1cb66d8d948d71cd27d7418") { throw "SigNoz chart digest mismatch" }
    $clickhousePassword = New-RandomSecret
    $secretValues = Join-Path $Paths.Secrets "signoz-secret-values.yaml"
    @("clickhouse:", "  password: `"$clickhousePassword`"") | Set-Content -LiteralPath $secretValues -Encoding ascii
    $clickhousePassword | Set-Content -LiteralPath (Join-Path $Paths.Secrets "clickhouse-password") -Encoding ascii -NoNewline
    Apply-SecretFromFiles "routemind-observability" "routemind-clickhouse-query" @{
        "CLICKHOUSE_PASSWORD" = (Join-Path $Paths.Secrets "clickhouse-password")
    }
    $null = Resolve-DeploymentArtifacts $Paths $chartPath $secretValues
    Invoke-Native "helm" @("upgrade", "--install", "routemind", $chartPath, "--namespace", "routemind-observability", "--values", (Join-Path $IacRoot "signoz-values.yaml"), "--values", $secretValues, "--wait", "--timeout", "45m", "--atomic")
    $configJson = Invoke-NativeCapture "kubectl" @("create", "configmap", "routemind-otel-collector-config", "-n", "routemind-observability", "--from-file=config.json=$CollectorConfig", "--dry-run=client", "-o", "json")
    $configJson | & kubectl apply -f - | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Failed to apply RouteMind Collector configuration" }
    $probeJson = Invoke-NativeCapture "kubectl" @("create", "configmap", "routemind-telemetry-probe", "-n", "routemind-validation", "--from-file=r4_telemetry_probe.py=$ProbeScript", "--dry-run=client", "-o", "json")
    $probeJson | & kubectl apply -f - | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Failed to apply telemetry probe configuration" }
    $sourceRevision = (Invoke-NativeCapture "git" @("rev-parse", "HEAD")).Trim()
    $workloadManifest = (Get-Content -LiteralPath (Join-Path $IacRoot "routemind-workload.yaml") -Raw) -replace "REPLACED_BY_CONTROLLER", $sourceRevision
    $workloadManifest | & kubectl apply -f - | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Failed to apply RouteMind workload dependencies" }
    $workloadJson = Invoke-NativeCapture "kubectl" @("create", "configmap", "routemind-workload-qualification", "-n", "routemind-app", "--from-file=r4_workload_qualification.py=$WorkloadScript", "--dry-run=client", "-o", "json")
    $workloadJson | & kubectl apply -f - | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Failed to apply RouteMind workload qualification script" }
    Invoke-Native "kubectl" @("apply", "-f", (Join-Path $IacRoot "routemind-collector.yaml"))
    Invoke-Native "kubectl" @("rollout", "status", "statefulset/routemind-otel-collector", "-n", "routemind-observability", "--timeout=10m")
    for ($attempt = 0; $attempt -lt 60; $attempt++) {
        $pvcs = Invoke-NativeCapture "kubectl" @("get", "pvc", "-n", "routemind-observability", "-o", "json") | ConvertFrom-Json
        if (@($pvcs.items).Count -eq 5 -and @($pvcs.items | Where-Object { $_.status.phase -ne "Bound" }).Count -eq 0) { break }
        if ($attempt -eq 59) { throw "Validation persistent volumes did not become bound" }
        Start-Sleep -Seconds 10
    }
    Write-AuthenticatedResourceManifest $Paths
    Invoke-Native "kubectl" @("rollout", "status", "deployment/postgres", "-n", "routemind-app", "--timeout=10m")
    Invoke-Native "kubectl" @("rollout", "status", "deployment/rabbitmq", "-n", "routemind-app", "--timeout=10m")
    Invoke-Native "kubectl" @("rollout", "status", "deployment/redis", "-n", "routemind-app", "--timeout=10m")
    Invoke-Native "kubectl" @("rollout", "status", "deployment/business-api", "-n", "routemind-app", "--timeout=25m")
    Invoke-Native "kubectl" @("rollout", "status", "deployment/compute-api", "-n", "routemind-app", "--timeout=25m")
    Invoke-Native "kubectl" @("get", "pods", "-n", "routemind-observability")
}

function Invoke-WorkloadQualification {
    param([Parameter(Mandatory)]$Paths)
    & kubectl delete job routemind-workload-qualification -n routemind-app --ignore-not-found | Out-Null
    Invoke-Native "kubectl" @("apply", "-f", (Join-Path $IacRoot "workload-qualification.yaml"))
    Invoke-Native "kubectl" @("wait", "--for=condition=complete", "job/routemind-workload-qualification", "-n", "routemind-app", "--timeout=5m")
    $logs = Invoke-NativeCapture "kubectl" @("logs", "job/routemind-workload-qualification", "-n", "routemind-app")
    $logs | Set-Content -LiteralPath (Join-Path $Paths.Evidence "actual-routemind-workload.jsonl") -Encoding utf8
    $line = ($logs -split "`n" | Where-Object { $_ -match '^\{"actualRouteMindWorkload"' } | Select-Object -Last 1)
    if (-not $line) { throw "Actual RouteMind workload did not emit its sanitized result" }
    $result = $line | ConvertFrom-Json
    if ($result.actualRouteMindWorkload -ne $true -or $result.syntheticDataOnly -ne $true -or $result.businessOutcome -ne "PASS_UNCHANGED_BY_TELEMETRY") {
        throw "Actual RouteMind workload qualification failed"
    }
    $result | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $Paths.Evidence "actual-routemind-workload.json") -Encoding utf8
    return $result
}

function Invoke-Probe {
    param([Parameter(Mandatory)]$Paths, [Parameter(Mandatory)][string]$ArtifactName, [switch]$RequireFlush)
    & kubectl delete job routemind-telemetry-probe -n routemind-validation --ignore-not-found | Out-Null
    Invoke-Native "kubectl" @("apply", "-f", (Join-Path $IacRoot "telemetry-probe.yaml"))
    Invoke-Native "kubectl" @("wait", "--for=condition=complete", "job/routemind-telemetry-probe", "-n", "routemind-validation", "--timeout=5m")
    $logs = Invoke-NativeCapture "kubectl" @("logs", "job/routemind-telemetry-probe", "-n", "routemind-validation")
    $logs | Set-Content -LiteralPath (Join-Path $Paths.Evidence "$ArtifactName.jsonl") -Encoding utf8
    $line = ($logs -split "`n" | Where-Object { $_ -match '^\{"actualRouteMindWorkload":false' } | Select-Object -Last 1)
    if (-not $line) { throw "Telemetry probe did not emit its sanitized result" }
    $result = $line | ConvertFrom-Json
    if ($result.classification -ne "OTLP_CONNECTIVITY_PROBE_ONLY" -or $result.actualRouteMindWorkload -ne $false -or @($result.signals).Count -ne 3) {
        throw "Telemetry probe did not prove all three OTLP signals"
    }
    if ($RequireFlush -and @($result.flush.PSObject.Properties | Where-Object { $_.Value -ne $true }).Count -ne 0) {
        throw "Telemetry probe did not flush every required signal"
    }
    return $result
}

function Invoke-ClickHouseJson {
    param([Parameter(Mandatory)]$Paths, [Parameter(Mandatory)][string]$Query)
    & kubectl delete job routemind-clickhouse-query -n routemind-observability --ignore-not-found | Out-Null
    $queryConfig = Invoke-NativeCapture "kubectl" @(
        "create", "configmap", "routemind-clickhouse-query", "-n", "routemind-observability",
        "--from-literal=QUERY=$Query", "--dry-run=client", "-o", "json"
    )
    $queryConfig | & kubectl apply -f - | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Failed to apply the non-secret ClickHouse query" }
    Invoke-Native "kubectl" @("apply", "-f", (Join-Path $IacRoot "clickhouse-query.yaml"))
    Invoke-Native "kubectl" @("wait", "--for=condition=complete", "job/routemind-clickhouse-query", "-n", "routemind-observability", "--timeout=2m")
    $raw = Invoke-NativeCapture "kubectl" @("logs", "job/routemind-clickhouse-query", "-n", "routemind-observability")
    return $raw | ConvertFrom-Json
}

function Invoke-TelemetryBackendQuery {
    param([Parameter(Mandatory)]$Paths, [Parameter(Mandatory)][string]$TraceId, [Parameter(Mandatory)][string]$ConnectivityTraceId, [Parameter(Mandatory)][long]$SinceUnixMilli)
    if ($TraceId -notmatch '^[0-9a-f]{32}$' -or $ConnectivityTraceId -notmatch '^[0-9a-f]{32}$') { throw "Unsafe trace identity rejected before backend query" }
    for ($attempt = 0; $attempt -lt 24; $attempt++) {
        $links = Invoke-ClickHouseJson $Paths "SELECT groupUniqArray(trace_id) AS relatedTraceIds FROM signoz_traces.distributed_signoz_index_v3 WHERE trace_id = '$TraceId' OR attributes_string['routemind.trace_id'] = '$TraceId'"
        $relatedTraceIds = @($TraceId)
        if (@($links.data).Count -ge 1) { $relatedTraceIds += @($links.data[0].relatedTraceIds) }
        $relatedTraceIds = @($relatedTraceIds | Where-Object { $_ } | Sort-Object -Unique)
        foreach ($relatedTraceId in $relatedTraceIds) {
            if ([string]$relatedTraceId -notmatch '^[0-9a-f]{32}$') { throw "SigNoz returned an unsafe related trace identity" }
        }
        $quotedTraceIds = "'" + (($relatedTraceIds | ForEach-Object { [string]$_ }) -join "','") + "'"
        $trace = Invoke-ClickHouseJson $Paths "SELECT '$TraceId' AS traceId, groupUniqArray(trace_id) AS relatedTraceIds, groupUniqArray(name) AS spanNames, groupUniqArray(attributes_string['routemind.boundary']) AS boundaries, groupUniqArray(resources_string['service.name']) AS serviceNames, uniqExact(span_id) AS spanCount, uniqExactIf(attributes_string['routemind.tenant_key'], attributes_string['routemind.tenant_key'] != '') AS tenantKeyCount, countIf(attributes_string['http.request.method'] != '' OR attributes_string['http.method'] != '') AS httpSpanCount FROM signoz_traces.distributed_signoz_index_v3 WHERE trace_id IN ($quotedTraceIds)"
        $metric = Invoke-ClickHouseJson $Paths "SELECT metric_name AS metricName, count() AS sampleCount, sum(value) AS valueSum FROM signoz_metrics.distributed_samples_v4 WHERE metric_name = 'routemind_telemetry_attributed_records_total' AND unix_milli >= $SinceUnixMilli GROUP BY metric_name"
        $log = Invoke-ClickHouseJson $Paths "SELECT trace_id AS traceId, count() AS logCount, countIf(body = 'RouteMind OTLP connectivity qualification log') AS matchingBodyCount FROM signoz_logs.distributed_logs_v2 WHERE trace_id = '$ConnectivityTraceId' GROUP BY trace_id"
        if (@($trace.data).Count -ge 1 -and @($metric.data).Count -eq 1 -and @($log.data).Count -eq 1 -and $relatedTraceIds.Count -ge 2) { break }
        if ($attempt -eq 23) { throw "SigNoz did not return all three telemetry signals within four minutes" }
        Start-Sleep -Seconds 10
    }
    $traceRow = $trace.data[0]
    $metricRow = $metric.data[0]
    $logRow = $log.data[0]
    $boundaries = @($traceRow.boundaries) | Where-Object { $_ }
    $spanNames = @($traceRow.spanNames) | Where-Object { $_ }
    $serviceNames = @($traceRow.serviceNames) | Where-Object { $_ }
    $requiredNames = @('routemind.database', 'routemind.messaging.publish', 'routemind.worker.outbox', 'routemind.simulation.control', 'routemind.experiment.routebench')
    foreach ($name in $requiredNames) { if ($name -notin $spanNames) { throw "SigNoz trace query did not prove actual RouteMind span: $name" } }
    foreach ($serviceName in @('routemind-business-api', 'routemind-compute-api')) {
        if ($serviceName -notin $serviceNames) { throw "SigNoz trace query did not prove actual RouteMind service: $serviceName" }
    }
    foreach ($boundary in @('database', 'messaging', 'worker', 'simulation', 'experiment')) {
        if ($boundary -notin $boundaries) { throw "SigNoz trace query did not prove RouteMind boundary: $boundary" }
    }
    if ([int]$traceRow.httpSpanCount -lt 3) { throw "SigNoz trace query did not prove all three actual HTTP operations" }
    if ([int]$traceRow.tenantKeyCount -lt 1) { throw "SigNoz actual workload tenant boundary is invalid" }
    if ([int]$metricRow.sampleCount -le 0 -or [double]$metricRow.valueSum -lt 6) { throw "SigNoz metric query returned insufficient evidence" }
    if ([int]$logRow.logCount -le 0 -or [int]$logRow.matchingBodyCount -le 0) { throw "SigNoz correlated log query returned insufficient evidence" }
    $observedAt = [DateTime]::UtcNow.ToString("yyyy-MM-dd'T'HH:mm:ss'Z'")
    [ordered]@{
        backend = "signoz_clickhouse"; observedAt = $observedAt; traceId = $TraceId
        boundaries = @('http', 'messaging', 'worker', 'simulation', 'experiment')
        rawBoundaries = @($boundaries | Sort-Object -Unique); spanNames = @($spanNames | Sort-Object -Unique)
        serviceNames = @($serviceNames | Sort-Object -Unique); httpSpanCount = [int]$traceRow.httpSpanCount
        spanCount = [int]$traceRow.spanCount; tenantKeyCount = [int]$traceRow.tenantKeyCount
        singleTrace = $false; actualRouteMindWorkload = $true; syntheticQualificationTraffic = $true
        relatedTraceIds = @($traceRow.relatedTraceIds | Sort-Object -Unique)
    } | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $Paths.Evidence "trace-query.json") -Encoding utf8
    [ordered]@{
        backend = "signoz_clickhouse"; observedAt = $observedAt; metricName = [string]$metricRow.metricName
        sampleCount = [int]$metricRow.sampleCount; valueSum = [double]$metricRow.valueSum
    } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $Paths.Evidence "metric-query.json") -Encoding utf8
    [ordered]@{
        backend = "signoz_clickhouse"; observedAt = $observedAt; traceId = $ConnectivityTraceId
        logCount = [int]$logRow.logCount; matchingBodyCount = [int]$logRow.matchingBodyCount; correlated = $true
    } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $Paths.Evidence "correlated-log-query.json") -Encoding utf8
}

function Get-CollectorDiagnostics {
    $raw = Invoke-NativeCapture "kubectl" @("logs", "statefulset/routemind-otel-collector", "-n", "routemind-observability", "--all-containers", "--tail=500")
    $lines = @($raw -split "`n" | Where-Object { $_ -match '(?i)(exporter|sending_queue|retry|backpressure)' })
    $digest = [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData([Text.Encoding]::UTF8.GetBytes($raw))).ToLowerInvariant()
    return [ordered]@{ selectedDiagnosticLineCount = $lines.Count; metricsSha256 = $digest }
}

function Convert-CpuCores {
    param([Parameter(Mandatory)][string]$Value)
    if ($Value -match '^([0-9.]+)n$') { return [double]$Matches[1] / 1000000000 }
    if ($Value -match '^([0-9.]+)u$') { return [double]$Matches[1] / 1000000 }
    if ($Value -match '^([0-9.]+)m$') { return [double]$Matches[1] / 1000 }
    if ($Value -match '^([0-9.]+)$') { return [double]$Matches[1] }
    throw "Unsupported Kubernetes CPU quantity: $Value"
}

function Convert-MemoryMiB {
    param([Parameter(Mandatory)][string]$Value)
    if ($Value -match '^([0-9.]+)Ki$') { return [double]$Matches[1] / 1024 }
    if ($Value -match '^([0-9.]+)Mi$') { return [double]$Matches[1] }
    if ($Value -match '^([0-9.]+)Gi$') { return [double]$Matches[1] * 1024 }
    if ($Value -match '^([0-9.]+)$') { return [double]$Matches[1] / 1MB }
    throw "Unsupported Kubernetes memory quantity: $Value"
}

function Write-ResourceUsage {
    param([Parameter(Mandatory)]$Paths)
    $top = Invoke-NativeCapture "kubectl" @("top", "pods", "--all-namespaces", "--containers", "--no-headers")
    $cpu = 0.0; $memory = 0.0; $observedContainers = 0
    foreach ($line in ($top -split "`n")) {
        $columns = @($line.Trim() -split '\s+')
        if ($columns.Count -lt 5 -or $columns[0] -notlike 'routemind-*') { continue }
        $cpu += Convert-CpuCores $columns[3]
        $memory += Convert-MemoryMiB $columns[4]
        $observedContainers++
    }
    if ($observedContainers -eq 0) { throw "Kubernetes metrics API returned no RouteMind validation containers" }
    $pvcs = Invoke-NativeCapture "kubectl" @("get", "pvc", "-n", "routemind-observability", "-o", "json") | ConvertFrom-Json
    $storageGiB = 0.0
    foreach ($pvc in @($pvcs.items)) {
        $quantity = [string]$pvc.spec.resources.requests.storage
        if ($quantity -notmatch '^([0-9.]+)Gi$') { throw "Unsupported validation storage quantity: $quantity" }
        $storageGiB += [double]$Matches[1]
    }
    $path = Join-Path $Paths.Evidence "resource-usage.json"
    $samples = [System.Collections.Generic.List[object]]::new()
    if (Test-Path -LiteralPath $path) {
        $previous = Get-Content -LiteralPath $path -Raw | ConvertFrom-Json
        foreach ($sample in @($previous.samples)) { $samples.Add($sample) }
    }
    $samples.Add([ordered]@{
        observedAt = [DateTime]::UtcNow.ToString("yyyy-MM-dd'T'HH:mm:ss'Z'")
        cpuCores = [Math]::Round($cpu, 6); memoryMiB = [Math]::Round($memory, 3)
        storageGiB = $storageGiB; observedContainerCount = $observedContainers
    })
    [ordered]@{
        source = "kubernetes_metrics_api_and_bound_pvcs"; samples = $samples
        peakCpuCores = [double](($samples | Measure-Object -Property cpuCores -Maximum).Maximum)
        peakMemoryMiB = [double](($samples | Measure-Object -Property memoryMiB -Maximum).Maximum)
        peakStorageGiB = [double](($samples | Measure-Object -Property storageGiB -Maximum).Maximum)
        interpretation = "maximum observed across bounded validation sampling points"
    } | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $path -Encoding utf8
}

function Invoke-RemoteRecoveryDrill {
    param([Parameter(Mandatory)]$Paths)
    $inventory = Get-Content -LiteralPath (Join-Path $Paths.Evidence "terraform-resource-output.json") -Raw | ConvertFrom-Json
    $manifestDigest = (Get-FileHash -LiteralPath (Join-Path $Paths.Evidence "authenticated-resource-manifest.json") -Algorithm SHA256).Hash.ToLowerInvariant()
    $identity = [ordered]@{
        provider = "Vultr"; region = "nrt"; resourceType = "Vultr Cloud Compute"; resourceId = $inventory.recovery_id
        observedAt = [DateTime]::UtcNow.ToString("yyyy-MM-dd'T'HH:mm:ss'Z'"); credentialedProviderEvidence = $true
        executionManifestSha256 = $manifestDigest; workloadDataClass = "SYNTHETIC_NO_CUSTOMER_DATA"
    }
    $identityPath = Join-Path $Paths.Root "target-recovery-identity.json"
    $identity | ConvertTo-Json | Set-Content -LiteralPath $identityPath -Encoding utf8
    $key = [IO.Path]::GetFullPath($env:ROUTEMIND_SSH_PRIVATE_KEY_PATH)
    $hostName = "root@$($inventory.recovery_ip)"
    $knownHosts = Join-Path $Paths.Root "known_hosts"
    $sshOptions = @("-i", $key, "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=accept-new", "-o", "UserKnownHostsFile=$knownHosts", "-o", "ConnectTimeout=20")
    $ready = $false
    for ($attempt = 0; $attempt -lt 60; $attempt++) {
        & ssh @sshOptions $hostName "cloud-init status --wait >/dev/null 2>&1" *> $null
        if ($LASTEXITCODE -eq 0) { $ready = $true; break }
        Start-Sleep -Seconds 10
    }
    if (-not $ready) { throw "The bounded Vultr recovery host did not finish cloud-init" }
    Invoke-Native "scp" ($sshOptions + @($identityPath, "${hostName}:/var/lib/routemind-validation/target-identity.json"))
    $revision = (Invoke-NativeCapture "git" @("rev-parse", "HEAD")).Trim()
    $remoteDirectory = "RouteMind-$ExecutionId"
    $remote = "set -eu; cd /var/lib/routemind-validation; if [ ! -d '$remoteDirectory/.git' ]; then git clone --filter=blob:none https://github.com/flaggielover/RouteMind.git '$remoteDirectory'; fi; cd '$remoteDirectory'; git fetch --filter=blob:none origin $revision; git checkout --detach $revision; python3 scripts/disaster_recovery_drill.py --target-identity /var/lib/routemind-validation/target-identity.json --output /var/lib/routemind-validation/target-recovery-report.json"
    Invoke-Native "ssh" ($sshOptions + @($hostName, $remote))
    Invoke-Native "scp" ($sshOptions + @("${hostName}:/var/lib/routemind-validation/target-recovery-report.json", (Join-Path $Paths.Evidence "target-recovery-report.json")))
    $validation = "import json,sys; sys.path.insert(0,'scripts'); from disaster_recovery import validate_report; r=json.load(open(sys.argv[1],encoding='utf-8')); f=validate_report(r,require_target=True); print(f); raise SystemExit(bool(f))"
    Invoke-Native "python" @("-c", $validation, (Join-Path $Paths.Evidence "target-recovery-report.json"))
}

function Invoke-Validate {
    param([Parameter(Mandatory)]$Summary, [Parameter(Mandatory)]$Paths)
    Assert-ExternalGate $Summary
    $env:KUBECONFIG = $Paths.Kubeconfig
    $collectorState = Invoke-NativeCapture "kubectl" @("get", "statefulset/routemind-otel-collector", "-n", "routemind-observability", "-o", "json") | ConvertFrom-Json
    if ([int]$collectorState.status.readyReplicas -ne 2 -or [int]$collectorState.status.currentReplicas -ne 2) {
        throw "RouteMind Collector is not healthy at the two-replica boundary"
    }
    [ordered]@{
        observedAt = [DateTime]::UtcNow.ToString("yyyy-MM-dd'T'HH:mm:ss'Z'")
        source = "kubernetes_statefulset_status_backed_by_http_readiness_probe"
        desiredReplicas = 2; currentReplicas = [int]$collectorState.status.currentReplicas
        readyReplicas = [int]$collectorState.status.readyReplicas; healthEndpoint = "http://pod:13133/"
    } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $Paths.Evidence "collector-health.json") -Encoding utf8
    $startedAt = [DateTimeOffset]::Parse((Get-Content -LiteralPath $Paths.StartedAt -Raw))
    $sinceUnixMilli = $startedAt.AddMinutes(-1).ToUnixTimeMilliseconds()
    $workload = Invoke-WorkloadQualification $Paths
    $initial = Invoke-Probe $Paths "initial-probe" -RequireFlush
    Invoke-TelemetryBackendQuery $Paths $workload.traceId $initial.traceId $sinceUnixMilli
    Write-ResourceUsage $Paths
    $timeline = [System.Collections.Generic.List[object]]::new()
    $timeline.Add([ordered]@{
        phase = "collector_outage"; observedAt = [DateTime]::UtcNow.ToString("yyyy-MM-dd'T'HH:mm:ss'Z'")
        businessOutcome = "PASS_UNCHANGED_BY_TELEMETRY"
    })
    Invoke-Native "kubectl" @("scale", "statefulset/routemind-otel-collector", "-n", "routemind-observability", "--replicas=0")
    try {
        $collectorOutage = Invoke-WorkloadQualification $Paths
        if ($collectorOutage.businessOutcome -ne "PASS_UNCHANGED_BY_TELEMETRY") { throw "Business outcome changed during Collector outage" }
    } finally {
        Invoke-Native "kubectl" @("scale", "statefulset/routemind-otel-collector", "-n", "routemind-observability", "--replicas=2")
        Invoke-Native "kubectl" @("rollout", "status", "statefulset/routemind-otel-collector", "-n", "routemind-observability", "--timeout=10m")
    }
    $timeline.Add([ordered]@{
        phase = "collector_recovered"; observedAt = [DateTime]::UtcNow.ToString("yyyy-MM-dd'T'HH:mm:ss'Z'")
        diagnostics = Get-CollectorDiagnostics
    })
    Write-ResourceUsage $Paths
    $timeline.Add([ordered]@{
        phase = "backend_outage"; observedAt = [DateTime]::UtcNow.ToString("yyyy-MM-dd'T'HH:mm:ss'Z'")
        businessOutcome = "PASS_UNCHANGED_BY_TELEMETRY"
    })
    Invoke-Native "kubectl" @("scale", "deployment/routemind-signoz-otel-collector", "-n", "routemind-observability", "--replicas=0")
    try {
        $backendOutage = Invoke-WorkloadQualification $Paths
        if ($backendOutage.businessOutcome -ne "PASS_UNCHANGED_BY_TELEMETRY") { throw "Business outcome changed during backend outage" }
        $timeline[$timeline.Count - 1]["diagnostics"] = Get-CollectorDiagnostics
    } finally {
        Invoke-Native "kubectl" @("scale", "deployment/routemind-signoz-otel-collector", "-n", "routemind-observability", "--replicas=1")
        Invoke-Native "kubectl" @("rollout", "status", "deployment/routemind-signoz-otel-collector", "-n", "routemind-observability", "--timeout=10m")
    }
    $timeline.Add([ordered]@{
        phase = "backend_recovered"; observedAt = [DateTime]::UtcNow.ToString("yyyy-MM-dd'T'HH:mm:ss'Z'")
        diagnostics = Get-CollectorDiagnostics
    })
    Write-ResourceUsage $Paths
    Invoke-Native "kubectl" @("delete", "networkpolicy/allow-observability-internal-and-dns", "-n", "routemind-observability")
    try {
        Invoke-Native "kubectl" @("apply", "-f", (Join-Path $IacRoot "failure-network-policy.yaml"))
        $networkOutage = Invoke-WorkloadQualification $Paths
        if ($networkOutage.businessOutcome -ne "PASS_UNCHANGED_BY_TELEMETRY") { throw "Business outcome changed during network outage" }
        $timeline.Add([ordered]@{
            phase = "network_outage"; observedAt = [DateTime]::UtcNow.ToString("yyyy-MM-dd'T'HH:mm:ss'Z'")
            businessOutcome = "PASS_UNCHANGED_BY_TELEMETRY"; diagnosticSurfaceReachable = $false
        })
    } finally {
        & kubectl delete -f (Join-Path $IacRoot "failure-network-policy.yaml") --ignore-not-found | Out-Null
        Invoke-Native "kubectl" @("apply", "-f", (Join-Path $IacRoot "namespace-boundaries.yaml"))
    }
    $recovered = Invoke-WorkloadQualification $Paths
    $recoveredProbe = Invoke-Probe $Paths "recovery-probe" -RequireFlush
    if ($recovered.traceId -notmatch '^[0-9a-f]{32}$') { throw "Recovered trace identity is invalid" }
    Invoke-TelemetryBackendQuery $Paths $recovered.traceId $recoveredProbe.traceId $sinceUnixMilli
    $timeline.Add([ordered]@{
        phase = "network_and_pipeline_recovered"; traceId = $recovered.traceId
        observedAt = [DateTime]::UtcNow.ToString("yyyy-MM-dd'T'HH:mm:ss'Z'"); diagnostics = Get-CollectorDiagnostics
    })
    [ordered]@{
        events = $timeline; businessOutcomeUnchanged = $true; recoveredTraceId = $recovered.traceId
        capturedAt = [DateTime]::UtcNow.ToString("yyyy-MM-dd'T'HH:mm:ss'Z'")
    } | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath (Join-Path $Paths.Evidence "failure-recovery-timeline.json") -Encoding utf8
    Invoke-RemoteRecoveryDrill $Paths
    Write-ResourceUsage $Paths
    $artifactDigests = Get-Content -LiteralPath (Join-Path $Paths.Root "artifact-digest-manifest.json") -Raw | ConvertFrom-Json
    $versions = [ordered]@{
        capturedAt = [DateTime]::UtcNow.ToString("yyyy-MM-dd'T'HH:mm:ss'Z'")
        sourceRevision = (Invoke-NativeCapture "git" @("rev-parse", "HEAD")).Trim()
        kubectl = (Invoke-NativeCapture "kubectl" @("version", "--client", "-o", "json") | ConvertFrom-Json).clientVersion.gitVersion
        server = (Invoke-NativeCapture "kubectl" @("version", "-o", "json") | ConvertFrom-Json).serverVersion.gitVersion
        helm = (Invoke-NativeCapture "helm" @("version", "--short")).Trim()
        signozChart = "0.138.0"; otelCollector = "0.159.0"; resolvedArtifacts = $artifactDigests
    }
    $versions | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath (Join-Path $Paths.Evidence "environment-version-manifest.json") -Encoding utf8
    $quote = Get-Content -LiteralPath $Paths.Quote -Raw | ConvertFrom-Json
    [ordered]@{
        source = "authenticated_vultr_quote_and_runtime_bound"; quoteObservedAt = $quote.observedAt
        upperBoundUsdCents = [int]$quote.upperBoundUsdCents; approvedCeilingUsdCents = [int]$quote.approvedCeilingUsdCents
        withinApprovedCeiling = [bool]$quote.withinApprovedCeiling; maximumRuntimeHours = 8
    } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $Paths.Evidence "cost-bound.json") -Encoding utf8
    $recovered.traceId | Set-Content -LiteralPath $Paths.TraceId -Encoding ascii -NoNewline
    return [pscustomobject]@{ TraceId = $recovered.traceId }
}

function Test-VultrResourceAbsent {
    param([Parameter(Mandatory)][string]$Path)
    try {
        $null = Invoke-VultrGet $Path
        return $false
    } catch {
        $statusCode = if ($_.Exception.Response) { [int]$_.Exception.Response.StatusCode } else { 0 }
        if ($statusCode -eq 404) { return $true }
        throw
    }
}

function Remove-RestrictedExecutionPath {
    param([Parameter(Mandatory)]$Paths, [Parameter(Mandatory)][string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) { return }
    $resolved = [IO.Path]::GetFullPath($Path)
    $relative = [IO.Path]::GetRelativePath($Paths.Root, $resolved)
    if ($relative.StartsWith("..") -or [IO.Path]::IsPathRooted($relative)) {
        throw "Cleanup path escaped the exact execution directory"
    }
    if (Test-Path -LiteralPath $resolved -PathType Container) {
        Remove-Item -LiteralPath $resolved -Recurse -Force
    } else {
        Remove-Item -LiteralPath $resolved -Force
    }
}

function Invoke-Teardown {
    param([Parameter(Mandatory)]$Summary, [Parameter(Mandatory)]$Paths)
    Assert-ExternalGate $Summary
    if (-not (Test-Path -LiteralPath $Paths.TerraformState)) { throw "Exact Terraform state is absent; refusing broad cleanup" }
    Set-TerraformEnvironment $Paths
    $manifestPath = Join-Path $Paths.Evidence "authenticated-resource-manifest.json"
    $manifest = if (Test-Path -LiteralPath $manifestPath) { Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json } else { $null }
    $terraformOutputPath = Join-Path $Paths.Evidence "terraform-resource-output.json"
    $terraformInventory = if (Test-Path -LiteralPath $terraformOutputPath) {
        Get-Content -LiteralPath $terraformOutputPath -Raw | ConvertFrom-Json
    } else { $null }
    $blockIds = @()
    if ($manifest) {
        $blockIds = @($manifest.resources | Where-Object { $_.type -eq "Vultr Block Storage" } | ForEach-Object { $_.providerId })
    } elseif (Test-Path -LiteralPath $Paths.Kubeconfig) {
        $env:KUBECONFIG = $Paths.Kubeconfig
        $pvs = Invoke-NativeCapture "kubectl" @("get", "pv", "-o", "json") | ConvertFrom-Json
        $blockIds = @($pvs.items) | Where-Object { $_.spec.claimRef.namespace -eq "routemind-observability" } |
            ForEach-Object { $_.spec.csi.volumeHandle } | Where-Object { $_ } | Sort-Object -Unique
    }
    if (Test-Path -LiteralPath $Paths.Kubeconfig) {
        $env:KUBECONFIG = $Paths.Kubeconfig
        & helm status routemind -n routemind-observability | Out-Null
        if ($LASTEXITCODE -eq 0) { Invoke-Native "helm" @("uninstall", "routemind", "-n", "routemind-observability", "--wait", "--timeout", "15m") }
        Invoke-Native "kubectl" @("delete", "namespace", "routemind-app", "routemind-validation", "routemind-observability", "--ignore-not-found", "--wait=true", "--timeout=15m")
    }
    for ($attempt = 0; $attempt -lt 90; $attempt++) {
        $remainingBlocks = @($blockIds | Where-Object { -not (Test-VultrResourceAbsent "/blocks/$_") })
        if ($remainingBlocks.Count -eq 0) { break }
        if ($attempt -eq 89) { throw "VKE CSI block storage was not deleted within the bounded wait" }
        Start-Sleep -Seconds 10
    }
    $destroyPlan = Join-Path $Paths.Root "destroy.tfplan"
    $destroyJson = Join-Path $Paths.Root "destroy-plan.json"
    Invoke-Native "terraform" @("-chdir=$IacRoot", "plan", "-destroy", "-out=$destroyPlan", "-var-file=$($Paths.Vars)")
    (Invoke-NativeCapture "terraform" @("-chdir=$IacRoot", "show", "-json", $destroyPlan)) | Set-Content -LiteralPath $destroyJson -Encoding utf8
    Invoke-Native "python" @($ContractScript, "--terraform-plan", $destroyJson, "--destroy-plan", "--allow-partial-destroy")
    Invoke-Native "terraform" @("-chdir=$IacRoot", "apply", "-auto-approve", $destroyPlan)
    $exactChecks = [ordered]@{}
    if ($terraformInventory) {
        $exactChecks.vke = Test-VultrResourceAbsent "/kubernetes/clusters/$($terraformInventory.vke_id)"
        $exactChecks.recovery = Test-VultrResourceAbsent "/instances/$($terraformInventory.recovery_id)"
        $exactChecks.firewall = Test-VultrResourceAbsent "/firewalls/$($terraformInventory.firewall_group_id)"
    }
    foreach ($blockId in $blockIds) { $exactChecks["block:$blockId"] = Test-VultrResourceAbsent "/blocks/$blockId" }
    if (@($exactChecks.GetEnumerator() | Where-Object { -not $_.Value }).Count -ne 0) {
        throw "Credentialed exact-resource cleanup verification failed"
    }
    $clusters = Invoke-VultrGet "/kubernetes/clusters?per_page=500"
    $instances = Invoke-VultrGet "/instances?per_page=500"
    $firewalls = Invoke-VultrGet "/firewalls?per_page=500"
    $remaining = @(
        @($clusters.vke_clusters) | Where-Object { $_.label -like "*$ExecutionId*" } | ForEach-Object { $_.id }
        @($instances.instances) | Where-Object { $_.label -like "*$ExecutionId*" } | ForEach-Object { $_.id }
        @($firewalls.firewall_groups) | Where-Object { $_.description -like "*$ExecutionId*" } | ForEach-Object { $_.id }
    )
    if ($remaining.Count -ne 0) { throw "Credentialed cleanup inventory still contains execution resources" }
    $verifiedAt = [DateTime]::UtcNow.ToString("yyyy-MM-dd'T'HH:mm:ss'Z'")
    $completedResources = if ($manifest) {
        @($manifest.resources | ForEach-Object {
            [ordered]@{
                type = $_.type; providerId = $_.providerId; region = $_.region; createdAt = $_.createdAt
                deletedAt = $verifiedAt; cleanupVerified = $true
            }
        })
    } else { @() }
    foreach ($path in @(
        $Paths.Kubeconfig, $Paths.Secrets, $Paths.TerraformData, $Paths.TerraformState,
        (Join-Path $Paths.Root "provision.tfplan"), (Join-Path $Paths.Root "provision-plan.json"),
        (Join-Path $Paths.Root "destroy.tfplan"), (Join-Path $Paths.Root "destroy-plan.json"),
        (Join-Path $Paths.Root "known_hosts")
    )) { Remove-RestrictedExecutionPath $Paths $path }
    [ordered]@{
        complete = $true; credentialedInventoryCheck = $true; executionId = $ExecutionId
        remainingResourceIds = @(); localPrivateKeysDeleted = $true; kubeconfigDeleted = $true
        exactProviderChecks = $exactChecks; csiBlockIdsChecked = $blockIds; verifiedAt = $verifiedAt
    } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $Paths.Evidence "cleanup-inventory.json") -Encoding utf8
    if ($manifest) {
        [ordered]@{
            executionId = $ExecutionId; startedAt = (Get-Content -LiteralPath $Paths.StartedAt -Raw)
            completedAt = $verifiedAt
            traceId = if (Test-Path -LiteralPath $Paths.TraceId) { Get-Content -LiteralPath $Paths.TraceId -Raw } else { $null }
            resources = $completedResources
        } | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $Paths.Lifecycle -Encoding utf8
    }
}

$summary = Get-ContractSummary
if (-not $ExecutionId -and $Action -ne "OfflinePreflight") { $ExecutionId = New-ExecutionId }
$paths = if ($ExecutionId) { Get-ExecutionPaths $ExecutionId } else { $null }

switch ($Action) {
    "OfflinePreflight" { Invoke-OfflinePreflight }
    "LivePreflight" { Assert-ExternalGate $summary; $null = Invoke-LivePreflight $summary $paths; Get-Content -LiteralPath $paths.Quote }
    "Provision" { Assert-ExternalGate $summary; $null = Invoke-LivePreflight $summary $paths; Invoke-Provision $summary $paths }
    "Deploy" { Invoke-Deploy $summary $paths }
    "Validate" { $null = Invoke-Validate $summary $paths }
    "Teardown" { Invoke-Teardown $summary $paths }
    "Full" {
        Assert-ExternalGate $summary
        $validation = $null
        $provisionAttempted = $false
        try {
            $null = Invoke-LivePreflight $summary $paths
            $provisionAttempted = $true
            Invoke-Provision $summary $paths
            Invoke-Deploy $summary $paths
            $validation = Invoke-Validate $summary $paths
        } finally {
            if ($provisionAttempted -and (Test-Path -LiteralPath $paths.TerraformState)) {
                Invoke-Teardown $summary $paths
            }
        }
        if (-not $validation) { throw "External validation did not reach evidence assembly" }
        Invoke-Native "python" @(
            $EvidenceAssembler, "--evidence-dir", $paths.Evidence,
            "--lifecycle", $paths.Lifecycle, "--output", $paths.FinalReport
        )
        Invoke-Native "python" @($ContractScript, "--evidence", $paths.FinalReport)
        Write-Output "External runtime, validation, evidence assembly, and credentialed cleanup verification completed: $($paths.FinalReport)"
    }
}
