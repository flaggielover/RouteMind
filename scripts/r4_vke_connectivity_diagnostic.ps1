#Requires -Version 7.0

[CmdletBinding()]
param(
    [ValidateSet("OfflinePreflight", "LivePreflight", "Full")]
    [string]$Action = "OfflinePreflight",
    [string]$ExecutionId,
    [switch]$AcknowledgeExternalExecution
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Root = Split-Path -Parent $PSScriptRoot
$IacRoot = Join-Path $Root "infra/external-validation/vultr-tokyo-diagnostic"
$ContractScript = Join-Path $PSScriptRoot "r4_vke_connectivity_contract.py"
$PlanScript = Join-Path $PSScriptRoot "r4_vke_connectivity_plan.py"
$ProbeScript = Join-Path $PSScriptRoot "r4_vke_connectivity_diagnostic.py"
$PathSafetyScript = Join-Path $PSScriptRoot "path_safety.py"
$ContractPath = Join-Path $Root "contracts/external-validation/r4-vultr-tokyo-vke-connectivity-diagnostic-v2.json"
$DataRoot = if ($env:ROUTEMIND_DATA_ROOT) { [IO.Path]::GetFullPath($env:ROUTEMIND_DATA_ROOT) } else { [IO.Path]::GetFullPath((Join-Path (Split-Path -Parent $Root) "RouteMind-Data")) }
$relativeData = [IO.Path]::GetRelativePath($Root, $DataRoot)
if (-not $relativeData.StartsWith("..") -and -not [IO.Path]::IsPathRooted($relativeData)) { throw "ROUTEMIND_DATA_ROOT must remain outside the repository" }

function Invoke-NativeCapture {
    param([Parameter(Mandatory)][string]$Command, [string[]]$Arguments = @())
    $output = & $Command @Arguments
    if ($LASTEXITCODE -ne 0) { throw "$Command failed with exit code $LASTEXITCODE" }
    return ($output -join "`n")
}

function Invoke-Native {
    param([Parameter(Mandatory)][string]$Command, [string[]]$Arguments = @())
    & $Command @Arguments | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "$Command failed with exit code $LASTEXITCODE" }
}

function Require-Command {
    param([Parameter(Mandatory)][string]$Name)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) { throw "Required command is missing: $Name" }
}

function Invoke-VultrGet {
    param([Parameter(Mandatory)][string]$Path)
    return Invoke-RestMethod -Method Get -Uri "https://api.vultr.com/v2$Path" -Headers @{ Authorization = "Bearer $env:VULTR_API_KEY" } -TimeoutSec 30
}

function Test-VultrAbsent {
    param([Parameter(Mandatory)][string]$Path)
    try { $null = Invoke-VultrGet $Path; return $false }
    catch {
        if ($_.Exception.Response -and [int]$_.Exception.Response.StatusCode -eq 404) { return $true }
        throw
    }
}

function Wait-VultrAbsent {
    param([Parameter(Mandatory)][string]$Path, [int]$Attempts = 48)
    for ($attempt = 1; $attempt -le $Attempts; $attempt++) {
        try {
            if (Test-VultrAbsent $Path) { return $true }
        } catch { }
        if ($attempt -lt $Attempts) { Start-Sleep -Seconds 5 }
    }
    return $false
}

function New-ExecutionId {
    $revision = (Invoke-NativeCapture "git" @("rev-parse", "--short=10", "HEAD")).Trim()
    $stamp = [DateTime]::UtcNow.ToString("yyyyMMdd't'HHmmss'z'").ToLowerInvariant()
    return "r4-diag-$stamp-$revision"
}

function Get-ExecutionPaths {
    param([Parameter(Mandatory)][string]$Id)
    if ($Id -notmatch '^r4-diag-[0-9]{8}t[0-9]{6}z-[0-9a-f]{7,12}$') { throw "ExecutionId does not match the diagnostic format" }
    $rootPath = [IO.Path]::GetFullPath((Join-Path $DataRoot "external-validation/$Id"))
    $relative = [IO.Path]::GetRelativePath($DataRoot, $rootPath)
    if ($relative.StartsWith("..") -or [IO.Path]::IsPathRooted($relative)) { throw "Execution state escaped ROUTEMIND_DATA_ROOT" }
    return [pscustomobject]@{
        Root = $rootPath
        Evidence = Join-Path $rootPath "sanitized-evidence"
        TerraformData = Join-Path $rootPath "terraform-data"
        TerraformState = Join-Path $rootPath "terraform.tfstate"
        Vars = Join-Path $rootPath "execution.auto.tfvars.json"
        Quote = Join-Path $rootPath "authenticated-quote.json"
        Kubeconfig = Join-Path $rootPath "kubeconfig.yaml"
        StartedAt = Join-Path $rootPath "execution-started-at.txt"
        Lifecycle = Join-Path $rootPath "execution-lifecycle.json"
        OperatorProbe = Join-Path $rootPath "sanitized-evidence/operator-connectivity.json"
        TokyoProbe = Join-Path $rootPath "sanitized-evidence/tokyo-recovery-connectivity.json"
        Timeline = Join-Path $rootPath "sanitized-evidence/readiness-timeline.json"
        Firewall = Join-Path $rootPath "sanitized-evidence/firewall-readback.json"
        Failure = Join-Path $rootPath "sanitized-evidence/diagnostic-failure.json"
    }
}

function Initialize-State {
    param([Parameter(Mandatory)]$Paths)
    foreach ($path in @($Paths.Root, $Paths.Evidence, $Paths.TerraformData)) { New-Item -ItemType Directory -Path $path -Force | Out-Null }
    if (-not (Test-Path -LiteralPath $Paths.StartedAt)) { [DateTime]::UtcNow.ToString("yyyy-MM-dd'T'HH:mm:ss'Z'") | Set-Content -LiteralPath $Paths.StartedAt -Encoding ascii -NoNewline }
    if (Get-Command icacls -ErrorAction SilentlyContinue) { & icacls $Paths.Root /inheritance:r /grant:r "${env:USERNAME}:(OI)(CI)F" | Out-Null }
}

function Assert-Gate {
    if (-not $AcknowledgeExternalExecution) { throw "Mutating diagnostic execution requires -AcknowledgeExternalExecution" }
    $digest = (Invoke-NativeCapture "python" @($ContractScript)).Trim() | ConvertFrom-Json
    if ($env:ROUTEMIND_EXTERNAL_EXECUTION_APPROVAL_DIGEST -ne $digest.contractDigest) { throw "Diagnostic approval digest is absent or does not match the prepared contract" }
    foreach ($name in @("VULTR_API_KEY", "ROUTEMIND_SSH_PRIVATE_KEY_PATH", "ROUTEMIND_VULTR_SSH_KEY_ID", "ROUTEMIND_OPERATOR_CIDR")) {
        if ([string]::IsNullOrWhiteSpace([Environment]::GetEnvironmentVariable($name))) { throw "Required diagnostic configuration is absent: $name" }
    }
    Invoke-Native "python" @($PathSafetyScript, "--root", $Root, "--candidate-env", "ROUTEMIND_SSH_PRIVATE_KEY_PATH")
    $tracked = Invoke-NativeCapture "git" @("status", "--porcelain", "--untracked-files=no")
    if (-not [string]::IsNullOrWhiteSpace($tracked)) { throw "Diagnostic execution requires a clean tracked working tree" }
    $revision = (Invoke-NativeCapture "git" @("rev-parse", "HEAD")).Trim()
    $origin = (Invoke-NativeCapture "git" @("rev-parse", "origin/main")).Trim()
    $remoteLine = (Invoke-NativeCapture "git" @("ls-remote", "origin", "refs/heads/main")).Trim()
    if ($revision -ne $origin -or $remoteLine -notmatch "^$revision\s+refs/heads/main$") { throw "Diagnostic execution requires HEAD == origin/main" }
    return $digest
}

function Invoke-OfflinePreflight {
    Require-Command "python"
    Invoke-Native "python" @("-m", "py_compile", $ContractScript, $PlanScript, $ProbeScript)
    Invoke-Native "python" @($ContractScript)
    Invoke-Native "python" @(Join-Path $PSScriptRoot "r4_vke_connectivity_contract_test.py")
    Invoke-Native "python" @(Join-Path $PSScriptRoot "r4_vke_connectivity_diagnostic_test.py")
    Invoke-Native "python" @(Join-Path $PSScriptRoot "r4_vke_connectivity_plan_test.py")
    Invoke-Native "python" @(Join-Path $PSScriptRoot "r4_vke_connectivity_controller_test.py")
    Invoke-Native "python" @(Join-Path $PSScriptRoot "r4_external_validation_test.py")
    [pscustomobject]@{ valid = $true; action = "OfflinePreflight" } | ConvertTo-Json -Compress
}

function Invoke-LivePreflight {
    param([Parameter(Mandatory)]$Summary, [Parameter(Mandatory)]$Paths)
    $null = Assert-Gate
    Initialize-State $Paths
    $null = Invoke-VultrGet "/account"
    $regions = Invoke-VultrGet "/regions?per_page=500"
    $region = @($regions.regions) | Where-Object { $_.id -eq "nrt" } | Select-Object -First 1
    if (-not $region -or $region.city -ne "Tokyo" -or $region.country -ne "JP" -or "kubernetes" -notin @($region.options)) { throw "Authenticated Tokyo VKE region evidence is absent" }
    $availability = Invoke-VultrGet "/regions/nrt/availability"
    if ("vhp-4c-8gb-amd" -notin @($availability.available_plans) -or "vhp-2c-4gb-amd" -notin @($availability.available_plans)) { throw "Required diagnostic plan is unavailable in nrt" }
    $plans = Invoke-VultrGet "/plans?per_page=500"
    $worker = @($plans.plans) | Where-Object { $_.id -eq "vhp-4c-8gb-amd" } | Select-Object -First 1
    $recovery = @($plans.plans) | Where-Object { $_.id -eq "vhp-2c-4gb-amd" } | Select-Object -First 1
    if (-not $worker -or -not $recovery) { throw "Authenticated diagnostic pricing is incomplete" }
    $versions = Invoke-VultrGet "/kubernetes/versions"
    $version = @($versions.versions) | ForEach-Object { if ($_ -is [string]) { $_ } elseif ($_.version) { $_.version } elseif ($_.id) { $_.id } } | Where-Object { $_ -match '^v[0-9]+\.[0-9]+\.[0-9]+\+[0-9]+$' } | Select-Object -First 1
    if (-not $version) { throw "No supported VKE version returned" }
    $operatingSystems = Invoke-VultrGet "/os?per_page=500"
    $os = @($operatingSystems.os) | Where-Object { $_.name -match 'Ubuntu 24\.04.*x64' -and ($_.arch -eq "x64" -or -not $_.arch) } | Select-Object -First 1
    if (-not $os) { throw "No Ubuntu 24.04 x64 recovery image returned" }
    $upper = [int]([Math]::Ceiling(([double]$worker.hourly_cost + [double]$recovery.hourly_cost) * 2 * 100) + 200)
    if ($upper -gt 500) { throw "Diagnostic quote exceeds the approved USD 5 ceiling" }
    $clusters = Invoke-VultrGet "/kubernetes/clusters?per_page=500"
    $instances = Invoke-VultrGet "/instances?per_page=500"
    $firewalls = Invoke-VultrGet "/firewalls?per_page=500"
    $existing = @(
        @($clusters.vke_clusters) | Where-Object { $_.label -like "*${ExecutionId}*" } | ForEach-Object { $_.id }
        @($instances.instances) | Where-Object { $_.label -like "*${ExecutionId}*" } | ForEach-Object { $_.id }
        @($firewalls.firewall_groups) | Where-Object { $_.description -like "*${ExecutionId}*" } | ForEach-Object { $_.id }
    )
    if ($existing.Count -ne 0) { throw "Diagnostic execution identity already exists; refusing reuse" }
    $expires = [DateTime]::UtcNow.AddHours(2).ToString("yyyy-MM-dd'T'HH:mm:ss'Z'")
    [ordered]@{
        schemaVersion = 1; source = "authenticated_vultr_api"; observedAt = [DateTime]::UtcNow.ToString("yyyy-MM-dd'T'HH:mm:ss'Z'")
        provider = "Vultr"; region = "nrt"; city = "Tokyo"; country = "JP"; executionId = $ExecutionId
        vkeVersion = $version; recoveryOsId = [int]$os.id
        workerPlan = [ordered]@{ id = $worker.id; count = 1; hourlyUsd = [double]$worker.hourly_cost }
        recoveryPlan = [ordered]@{ id = $recovery.id; count = 1; hourlyUsd = [double]$recovery.hourly_cost }
        maximumRuntimeHours = 2; upperBoundUsdCents = $upper; incrementalCeilingUsdCents = 500; aggregatePriorAttemptsUpperBoundUsdCents = 660; aggregateCeilingUsdCents = 1500; withinApprovedCeiling = $true
    } | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $Paths.Quote -Encoding utf8
    [ordered]@{ execution_id = $ExecutionId; source_revision = (git rev-parse HEAD).Trim(); expires_at = $expires; vke_version = $version; recovery_os_id = [int]$os.id; ssh_key_id = $env:ROUTEMIND_VULTR_SSH_KEY_ID; operator_cidr = $env:ROUTEMIND_OPERATOR_CIDR } | ConvertTo-Json | Set-Content -LiteralPath $Paths.Vars -Encoding utf8
    return Get-Content -LiteralPath $Paths.Quote -Raw | ConvertFrom-Json
}

function Invoke-Terraform {
    param([Parameter(Mandatory)][string[]]$Arguments)
    $env:TF_DATA_DIR = $Paths.TerraformData
    Invoke-Native "terraform" (@("-chdir=$IacRoot") + $Arguments)
}

function Write-Artifact {
    param([Parameter(Mandatory)][string]$Path, [Parameter(Mandatory)]$Value)
    $Value | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $Path -Encoding utf8
}

function Invoke-Provision {
    param([Parameter(Mandatory)]$Paths)
    foreach ($tool in @("terraform", "python", "ssh", "scp")) { Require-Command $tool }
    Invoke-Terraform @("fmt", "-check")
    Invoke-Terraform @("init", "-reconfigure", "-backend-config=path=$($Paths.TerraformState)")
    $planPath = Join-Path $Paths.Root "diagnostic.tfplan"
    $planJson = Join-Path $Paths.Root "diagnostic-plan.json"
    Invoke-Terraform @("plan", "-input=false", "-out=$planPath", "-var-file=$($Paths.Vars)")
    (Invoke-NativeCapture "terraform" @("-chdir=$IacRoot", "show", "-json", $planPath)) | Set-Content -LiteralPath $planJson -Encoding utf8
    Invoke-Native "python" @($PlanScript, $planJson)
    $script:ProvisionApplyStarted = $true
    Invoke-Terraform @("apply", "-auto-approve", $planPath)
    $inventory = Invoke-NativeCapture "terraform" @("-chdir=$IacRoot", "output", "-json", "diagnostic_inventory")
    $inventory | Set-Content -LiteralPath (Join-Path $Paths.Evidence "terraform-resource-output.json") -Encoding utf8
    $kube = (Invoke-NativeCapture "terraform" @("-chdir=$IacRoot", "output", "-raw", "vke_kube_config")).Trim()
    [IO.File]::WriteAllBytes($Paths.Kubeconfig, [Convert]::FromBase64String($kube))
    return $inventory | ConvertFrom-Json
}

function Invoke-Readback {
    param([Parameter(Mandatory)]$Inventory, [Parameter(Mandatory)]$Paths)
    $firewall = Invoke-VultrGet "/firewalls/$($Inventory.vke_firewall_group_id)"
    $ruleResponse = Invoke-VultrGet "/firewalls/$($Inventory.vke_firewall_group_id)/rules"
    $rules = @($ruleResponse.firewall_rules)
    Write-Artifact $Paths.Firewall ([ordered]@{ firewallGroupId = $Inventory.vke_firewall_group_id; observedAt = [DateTime]::UtcNow.ToString("yyyy-MM-dd'T'HH:mm:ss'Z'"); rules = $rules })
    $expected = @($rules | Where-Object { $_.id -in @($Inventory.vke_api_operator_rule_id, $Inventory.vke_api_recovery_rule_id) })
    if ($expected.Count -ne 2) { throw "VKE firewall readback did not prove both diagnostic rules" }
    foreach ($rule in $expected) {
        if ($rule.protocol -ne "tcp" -or $rule.port -ne "6443" -or $rule.ip_type -ne "v4" -or $rule.subnet_size -ne 32) { throw "VKE diagnostic firewall rule shape drifted" }
    }
    $operatorRule = @($expected | Where-Object { $_.id -eq $Inventory.vke_api_operator_rule_id }) | Select-Object -First 1
    $recoveryRule = @($expected | Where-Object { $_.id -eq $Inventory.vke_api_recovery_rule_id }) | Select-Object -First 1
    $operatorNetwork = ([string]$env:ROUTEMIND_OPERATOR_CIDR).Split('/')[0]
    if (-not $operatorRule -or [string]$operatorRule.subnet -ne $operatorNetwork) { throw "Operator VKE API rule source does not match the configured /32" }
    if (-not $recoveryRule -or [string]$recoveryRule.subnet -ne [string]$Inventory.recovery_ip) { throw "Tokyo observer VKE API rule source does not match the recovery /32" }
}

function Invoke-RemoteProbe {
    param([Parameter(Mandatory)]$Inventory, [Parameter(Mandatory)]$Paths)
    $key = [IO.Path]::GetFullPath($env:ROUTEMIND_SSH_PRIVATE_KEY_PATH)
    $knownHosts = Join-Path $Paths.Root "known_hosts"
    $opts = @("-i", $key, "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=accept-new", "-o", "UserKnownHostsFile=$knownHosts", "-o", "ConnectTimeout=20")
    $hostName = "root@$($Inventory.recovery_ip)"
    $script:DiagnosticPhase = "tokyo_observer_ready"
    $ready = $false
    for ($i = 0; $i -lt 18; $i++) {
        & ssh @opts $hostName "cloud-init status --wait >/dev/null 2>&1 && test -r /var/lib/routemind-vke-diagnostic/identity && command -v python3 >/dev/null 2>&1" *> $null
        if ($LASTEXITCODE -eq 0) { $ready = $true; break }
        Start-Sleep -Seconds 5
    }
    if (-not $ready) { throw "Tokyo recovery observer identity and Python readiness did not become available" }
    $remoteScript = "/tmp/r4_vke_connectivity_diagnostic.py"
    $script:DiagnosticPhase = "tokyo_probe_copy"
    Invoke-Native "scp" ($opts + @($ProbeScript, "${hostName}:$remoteScript"))
    $endpoint = "https://$($Inventory.vke_endpoint):6443"
    $remoteCommand = "python3 $remoteScript --endpoint '$endpoint' --connect-host '$($Inventory.vke_ip)' --timeout 10 --max-addresses 1 --json"
    $script:DiagnosticPhase = "tokyo_probe_execution"
    $raw = (& ssh @opts $hostName $remoteCommand) -join "`n"
    if ($LASTEXITCODE -ne 0) { throw "Tokyo observer probe failed" }
    $raw | Set-Content -LiteralPath $Paths.TokyoProbe -Encoding utf8
    return $raw | ConvertFrom-Json
}

function Invoke-OperatorProbe {
    param([Parameter(Mandatory)]$Inventory, [Parameter(Mandatory)]$Paths)
    $script:DiagnosticPhase = "operator_probe"
    $endpoint = "https://$($Inventory.vke_endpoint):6443"
    Invoke-NativeCapture "python" @($ProbeScript, "--endpoint", $endpoint, "--connect-host", [string]$Inventory.vke_ip, "--kubeconfig", $Paths.Kubeconfig, "--timeout", "10", "--max-addresses", "1", "--json") | Set-Content -LiteralPath $Paths.OperatorProbe -Encoding utf8
    return Get-Content -LiteralPath $Paths.OperatorProbe -Raw | ConvertFrom-Json
}

function Invoke-Readiness {
    param([Parameter(Mandatory)]$Inventory, [Parameter(Mandatory)]$Paths)
    $records = [System.Collections.Generic.List[object]]::new()
    $delays = @(2, 4, 8, 16, 32, 32)
    for ($i = 0; $i -lt $delays.Count; $i++) {
        $operator = Invoke-OperatorProbe $Inventory $Paths
        $tokyo = Invoke-RemoteProbe $Inventory $Paths
        $provider = Invoke-VultrGet "/kubernetes/clusters/$($Inventory.vke_id)"
        $providerState = [string]$provider.vke_cluster.status
        $record = [ordered]@{
            observedAt = [DateTime]::UtcNow.ToString("yyyy-MM-dd'T'HH:mm:ss'Z'")
            attempt = $i + 1
            providerState = if ($providerState) { $providerState } else { "UNKNOWN" }
            operator = $operator.summary
            tokyoRecovery = $tokyo.summary
        }
        $records.Add($record)
        Write-Artifact $Paths.Timeline @($records)
        if ($operator.summary.tls -eq "TLS_OK" -and $tokyo.summary.tls -eq "TLS_OK") { return $records }
        Start-Sleep -Seconds $delays[$i]
    }
    return $records
}

function Invoke-Teardown {
    param([Parameter(Mandatory)]$Paths, [Parameter(Mandatory)]$Inventory)
    if (-not (Test-Path -LiteralPath $Paths.TerraformState)) { throw "Exact Terraform state is absent; refusing broad cleanup" }
    $destroyPlan = Join-Path $Paths.Root "diagnostic-destroy.tfplan"
    $destroyJson = Join-Path $Paths.Root "diagnostic-destroy-plan.json"
    Invoke-Terraform @("plan", "-destroy", "-input=false", "-out=$destroyPlan", "-var-file=$($Paths.Vars)")
    (Invoke-NativeCapture "terraform" @("-chdir=$IacRoot", "show", "-json", $destroyPlan)) | Set-Content -LiteralPath $destroyJson -Encoding utf8
    Invoke-Native "python" @($PlanScript, $destroyJson, "--destroy")
    Invoke-Terraform @("apply", "-auto-approve", $destroyPlan)
    $checks = [ordered]@{
        vke = Wait-VultrAbsent "/kubernetes/clusters/$($Inventory.vke_id)"
        recovery = Wait-VultrAbsent "/instances/$($Inventory.recovery_id)"
        recoveryFirewall = Wait-VultrAbsent "/firewalls/$($Inventory.recovery_firewall_group_id)"
        vkeFirewall = Wait-VultrAbsent "/firewalls/$($Inventory.vke_firewall_group_id)"
    }
    if (@($checks.GetEnumerator() | Where-Object { -not $_.Value }).Count -ne 0) { throw "Exact diagnostic cleanup checks did not converge" }
    $remaining = @()
    for ($attempt = 1; $attempt -le 48; $attempt++) {
        try {
            $clusters = Invoke-VultrGet "/kubernetes/clusters?per_page=500"
            $instances = Invoke-VultrGet "/instances?per_page=500"
            $firewalls = Invoke-VultrGet "/firewalls?per_page=500"
            $remaining = @(
                @($clusters.vke_clusters) | Where-Object { $_.label -like "*$ExecutionId*" } | ForEach-Object { $_.id }
                @($instances.instances) | Where-Object { $_.label -like "*$ExecutionId*" } | ForEach-Object { $_.id }
                @($firewalls.firewall_groups) | Where-Object { $_.description -like "*$ExecutionId*" } | ForEach-Object { $_.id }
            )
            if ($remaining.Count -eq 0) { break }
        } catch {
            $remaining = @("INVENTORY_CHECK_FAILED")
        }
        if ($attempt -lt 48) { Start-Sleep -Seconds 5 }
    }
    if ($remaining.Count -ne 0) { throw "Execution-label resources remain after teardown: $($remaining -join ',')" }
    [ordered]@{ complete = $true; credentialedInventoryCheck = $true; executionId = $ExecutionId; remainingResourceIds = @($remaining); executionLabelMatches = 0; exactProviderChecks = $checks; kubeconfigDeleted = $true; verifiedAt = [DateTime]::UtcNow.ToString("yyyy-MM-dd'T'HH:mm:ss'Z'") } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $Paths.Evidence "cleanup-inventory.json") -Encoding utf8
    foreach ($file in @($Paths.Kubeconfig, $Paths.TerraformData, $Paths.TerraformState, (Join-Path $Paths.Root "known_hosts"), (Join-Path $Paths.Root "diagnostic.tfplan"), (Join-Path $Paths.Root "diagnostic-plan.json"), $destroyPlan, $destroyJson)) { if (Test-Path -LiteralPath $file) { Remove-Item -LiteralPath $file -Recurse -Force } }
}

$summary = (Invoke-NativeCapture "python" @($ContractScript)).Trim() | ConvertFrom-Json
$script:ProvisionApplyStarted = $false
$script:DiagnosticPhase = "not_started"
if (-not $ExecutionId -and $Action -ne "OfflinePreflight") { $ExecutionId = New-ExecutionId }
$Paths = if ($ExecutionId) { Get-ExecutionPaths $ExecutionId } else { $null }

switch ($Action) {
    "OfflinePreflight" { Invoke-OfflinePreflight }
    "LivePreflight" { Assert-Gate; $null = Invoke-LivePreflight $summary $Paths; Get-Content -LiteralPath $Paths.Quote }
    "Full" {
        Assert-Gate
        $inventory = $null
        $failurePhase = $null
        $teardownFailure = $null
        try {
            $script:DiagnosticPhase = "live_preflight"
            $null = Invoke-LivePreflight $summary $Paths
            $script:DiagnosticPhase = "provision"
            $inventory = Invoke-Provision $Paths
            $script:DiagnosticPhase = "firewall_readback"
            Invoke-Readback $inventory $Paths
            $records = Invoke-Readiness $inventory $Paths
            $operator = Get-Content -LiteralPath $Paths.OperatorProbe -Raw | ConvertFrom-Json
            $tokyo = Get-Content -LiteralPath $Paths.TokyoProbe -Raw | ConvertFrom-Json
            $classification = if ($operator.summary.tls -eq "TLS_OK" -and $tokyo.summary.tls -eq "TLS_OK") { "BOTH_OBSERVERS_TLS_OK" } elseif ($tokyo.summary.tls -eq "TLS_OK") { "OPERATOR_PATH_SUSPECTED" } elseif ($operator.summary.tls -eq "TLS_OK") { "TOKYO_PATH_SUSPECTED" } else { "BOTH_OBSERVERS_FAILED" }
            [ordered]@{ executionId = $ExecutionId; classification = $classification; operator = $operator.summary; tokyoRecovery = $tokyo.summary; observedAt = [DateTime]::UtcNow.ToString("yyyy-MM-dd'T'HH:mm:ss'Z'") } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $Paths.Evidence "diagnostic-classification.json") -Encoding utf8
        } catch {
            $failurePhase = $script:DiagnosticPhase
            if (Test-Path -LiteralPath $Paths.Evidence) {
                Write-Artifact $Paths.Failure ([ordered]@{ executionId = $ExecutionId; classification = "DIAGNOSTIC_INCOMPLETE"; failurePhase = $failurePhase; errorType = $_.Exception.GetType().Name; observedAt = [DateTime]::UtcNow.ToString("yyyy-MM-dd'T'HH:mm:ss'Z'") })
            }
        } finally {
            if ($script:ProvisionApplyStarted -and -not $inventory -and (Test-Path -LiteralPath $Paths.Evidence)) {
                try {
                    $rawInventory = Invoke-NativeCapture "terraform" @("-chdir=$IacRoot", "output", "-json", "diagnostic_inventory")
                    $rawInventory | Set-Content -LiteralPath (Join-Path $Paths.Evidence "terraform-resource-output-recovered.json") -Encoding utf8
                    $inventory = $rawInventory | ConvertFrom-Json
                } catch { }
            }
            $script:DiagnosticPhase = "teardown"
            try {
                if ($script:ProvisionApplyStarted -and $inventory) { Invoke-Teardown $Paths $inventory }
                elseif ($script:ProvisionApplyStarted) { throw "Terraform apply started but exact inventory is unavailable; refusing broad cleanup" }
            } catch {
                $teardownFailure = $_.Exception.GetType().Name
            }
        }
        if ($teardownFailure) { throw "Diagnostic teardown failed closed after phase: $failurePhase" }
        if ($failurePhase) { throw "Diagnostic failed closed during phase: $failurePhase" }
        Write-Output "VKE diagnostic completed: $($Paths.Root)"
    }
}
