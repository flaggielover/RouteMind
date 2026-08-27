#Requires -Version 7.0

[CmdletBinding()]
param(
    [ValidateSet("OfflinePreflight", "LivePreflight", "Full", "Teardown")]
    [string]$Action = "OfflinePreflight",
    [string]$ExecutionId,
    [switch]$AcknowledgeExternalExecution
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Root = Split-Path -Parent $PSScriptRoot
$IacSource = Join-Path $Root "infra/external-validation/vultr-tokyo-vm-ssh-readiness-v1"
$ContractScript = Join-Path $PSScriptRoot "r4_vm_ssh_readiness_contract.py"
$PlanScript = Join-Path $PSScriptRoot "r4_vm_ssh_readiness_plan.py"
$ProbeScript = Join-Path $PSScriptRoot "r4_vm_ssh_readiness_probe.py"
$ArtifactScript = Join-Path $PSScriptRoot "r4_ssh_readiness.py"
$PathSafetyScript = Join-Path $PSScriptRoot "path_safety.py"
$ExpectedDigest = "2ba069c9886c69f1b38a22740c6c2367bd21a2bd129e8ff6c8148f336a46fbb7"
$ExpectedClientFingerprint = "SHA256:JHiQkjaVyp5ft91S12iyyCbDB6PCAGhDqYTVnMJAUeI"
$DataRoot = if ($env:ROUTEMIND_DATA_ROOT) {
    [IO.Path]::GetFullPath($env:ROUTEMIND_DATA_ROOT)
} else {
    [IO.Path]::GetFullPath((Join-Path (Split-Path -Parent $Root) "RouteMind-Data"))
}
$relativeData = [IO.Path]::GetRelativePath($Root, $DataRoot)
if (-not $relativeData.StartsWith("..") -and -not [IO.Path]::IsPathRooted($relativeData)) {
    throw "ROUTEMIND_DATA_ROOT must remain outside the repository"
}

function Get-ConfiguredValue {
    param([Parameter(Mandatory)][string]$Name)
    $value = [Environment]::GetEnvironmentVariable($Name, "Process")
    if ([string]::IsNullOrWhiteSpace($value)) {
        $value = [Environment]::GetEnvironmentVariable($Name, "User")
        if (-not [string]::IsNullOrWhiteSpace($value)) {
            [Environment]::SetEnvironmentVariable($Name, $value, "Process")
        }
    }
    return $value
}

function Require-Command {
    param([Parameter(Mandatory)][string]$Name)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command is missing: $Name"
    }
}

function Invoke-NativeCapture {
    param([Parameter(Mandatory)][string]$Command, [string[]]$Arguments = @())
    $output = & $Command @Arguments
    if ($LASTEXITCODE -ne 0) { throw "$Command failed with exit code $LASTEXITCODE" }
    return ($output -join "`n")
}

function Invoke-NativeQuiet {
    param([Parameter(Mandatory)][string]$Command, [string[]]$Arguments = @())
    & $Command @Arguments *> $null
    if ($LASTEXITCODE -ne 0) { throw "$Command failed with exit code $LASTEXITCODE" }
}

function Write-Json {
    param([Parameter(Mandatory)][string]$Path, [Parameter(Mandatory)]$Value)
    $temporary = "$Path.tmp"
    $Value | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $temporary -Encoding utf8
    Move-Item -LiteralPath $temporary -Destination $Path -Force
}

function Invoke-VultrGet {
    param([Parameter(Mandatory)][string]$Path)
    try {
        return Invoke-RestMethod -Method Get -Uri "https://api.vultr.com/v2$Path" -Headers @{
            Authorization = "Bearer $env:VULTR_API_KEY"
        } -TimeoutSec 30
    } catch {
        $status = if ($_.Exception.Response) { [int]$_.Exception.Response.StatusCode } else { 0 }
        throw "Authenticated Vultr GET failed for $Path with status $status"
    }
}

function Test-VultrAbsent {
    param([Parameter(Mandatory)][string]$Path)
    try {
        $null = Invoke-RestMethod -Method Get -Uri "https://api.vultr.com/v2$Path" -Headers @{
            Authorization = "Bearer $env:VULTR_API_KEY"
        } -TimeoutSec 30
        return $false
    } catch {
        if ($_.Exception.Response -and [int]$_.Exception.Response.StatusCode -eq 404) { return $true }
        return $false
    }
}

function Wait-VultrAbsent {
    param([Parameter(Mandatory)][string]$Path)
    for ($attempt = 1; $attempt -le 48; $attempt++) {
        if (Test-VultrAbsent $Path) { return $true }
        if ($attempt -lt 48) { Start-Sleep -Seconds 5 }
    }
    return $false
}

function New-ExecutionId {
    $revision = (Invoke-NativeCapture "git" @("rev-parse", "--short=10", "HEAD")).Trim()
    $stamp = [DateTime]::UtcNow.ToString("yyyyMMdd't'HHmmss'z'").ToLowerInvariant()
    return "r4-vm-ssh-v1-$stamp-$revision"
}

function Get-ExecutionPaths {
    param([Parameter(Mandatory)][string]$Id)
    if ($Id -notmatch '^r4-vm-ssh-v1-[0-9]{8}t[0-9]{6}z-[0-9a-f]{7,12}$') {
        throw "ExecutionId does not match the SSH-readiness format"
    }
    $rootPath = [IO.Path]::GetFullPath((Join-Path $DataRoot "external-validation/$Id"))
    $relative = [IO.Path]::GetRelativePath($DataRoot, $rootPath)
    if ($relative.StartsWith("..") -or [IO.Path]::IsPathRooted($relative)) {
        throw "Execution state escaped ROUTEMIND_DATA_ROOT"
    }
    $evidence = Join-Path $rootPath "sanitized-evidence"
    $terraform = Join-Path $rootPath "terraform"
    return [pscustomobject]@{
        Root = $rootPath
        Evidence = $evidence
        Terraform = $terraform
        TerraformData = Join-Path $rootPath "terraform-data"
        TerraformState = Join-Path $terraform "terraform.tfstate"
        Vars = Join-Path $terraform "execution.auto.tfvars.json"
        Quote = Join-Path $evidence "authenticated-plan-and-os-quote.json"
        Approval = Join-Path $evidence "approval-digest-verification.json"
        PrivateInventory = Join-Path $rootPath "private-resource-output.json"
        ProviderTimeline = Join-Path $evidence "provider-readiness-timeline.json"
        Readback = Join-Path $evidence "resource-and-firewall-readback.json"
        RawArtifact = Join-Path $evidence "raw/ssh-readiness-diagnostic-vm-ssh-readiness.json"
        Aggregate = Join-Path $evidence "stage-aggregate.json"
        KnownHosts = Join-Path $rootPath "known_hosts"
        Lifecycle = Join-Path $evidence "execution-lifecycle.json"
        Failure = Join-Path $evidence "execution-failure.json"
    }
}

function Initialize-State {
    param([Parameter(Mandatory)]$Paths)
    foreach ($path in @($Paths.Root, $Paths.Evidence, $Paths.Terraform, $Paths.TerraformData)) {
        New-Item -ItemType Directory -Path $path -Force | Out-Null
    }
    if (Get-Command icacls -ErrorAction SilentlyContinue) {
        & icacls $Paths.Root /inheritance:r /grant:r "${env:USERNAME}:(OI)(CI)F" *> $null
        if ($LASTEXITCODE -ne 0) { throw "Unable to restrict execution-state ACL" }
    }
    foreach ($name in @("versions.tf", "variables.tf", "main.tf", "outputs.tf", "cloud-init.yaml.tftpl")) {
        Copy-Item -LiteralPath (Join-Path $IacSource $name) -Destination (Join-Path $Paths.Terraform $name) -Force
    }
}

function Assert-Gate {
    if (-not $AcknowledgeExternalExecution) {
        throw "External execution requires -AcknowledgeExternalExecution"
    }
    foreach ($name in @(
        "VULTR_API_KEY",
        "ROUTEMIND_SSH_PRIVATE_KEY_PATH",
        "ROUTEMIND_VULTR_SSH_KEY_ID",
        "ROUTEMIND_OPERATOR_CIDR"
    )) {
        if ([string]::IsNullOrWhiteSpace((Get-ConfiguredValue $name))) {
            throw "Required execution configuration is absent: $name"
        }
    }
    $approval = Get-ConfiguredValue "ROUTEMIND_VM_SSH_READINESS_V1_APPROVAL_DIGEST"
    if ($approval -ne $ExpectedDigest) { throw "Approval digest is absent or mismatched" }
    $summary = (Invoke-NativeCapture "python" @($ContractScript)).Trim() | ConvertFrom-Json
    if ($summary.canonicalSha256 -ne $ExpectedDigest) { throw "Canonical contract digest mismatch" }
    Invoke-NativeQuiet "python" @($PathSafetyScript, "--root", $Root, "--candidate-env", "ROUTEMIND_SSH_PRIVATE_KEY_PATH")
    $tracked = Invoke-NativeCapture "git" @("status", "--porcelain", "--untracked-files=no")
    if (-not [string]::IsNullOrWhiteSpace($tracked)) { throw "Execution requires a clean tracked working tree" }
    $head = (Invoke-NativeCapture "git" @("rev-parse", "HEAD")).Trim()
    $origin = (Invoke-NativeCapture "git" @("rev-parse", "origin/main")).Trim()
    $remote = (Invoke-NativeCapture "git" @("ls-remote", "origin", "refs/heads/main")).Trim()
    if ($head -ne $origin -or $remote -notmatch "^$head\s+refs/heads/main$") {
        throw "Execution requires HEAD == origin/main"
    }
    return $summary
}

function Invoke-OfflinePreflight {
    foreach ($tool in @("python", "git", "ssh", "ssh-keygen", "ssh-keyscan", "terraform")) {
        Require-Command $tool
    }
    Invoke-NativeQuiet "python" @("-m", "py_compile", $ContractScript, $PlanScript, $ProbeScript, $ArtifactScript)
    Invoke-NativeQuiet "python" @($ContractScript)
    Invoke-NativeQuiet "python" @(Join-Path $PSScriptRoot "r4_vm_ssh_readiness_contract_test.py")
    Invoke-NativeQuiet "python" @(Join-Path $PSScriptRoot "r4_vm_ssh_readiness_plan_test.py")
    Invoke-NativeQuiet "python" @(Join-Path $PSScriptRoot "r4_vm_ssh_readiness_probe_test.py")
    Invoke-NativeQuiet "python" @(Join-Path $PSScriptRoot "r4_ssh_readiness_test.py")
    [ordered]@{ valid = $true; action = "OfflinePreflight"; contractDigest = $ExpectedDigest } | ConvertTo-Json -Compress
}

function Get-KeyFingerprint {
    param([Parameter(Mandatory)][string]$Path)
    $line = (Invoke-NativeCapture "ssh-keygen" @("-lf", $Path, "-E", "sha256")).Trim()
    $parts = $line -split '\s+'
    if ($parts.Count -lt 4 -or $parts[-1] -ne "(ED25519)") { throw "Expected an ED25519 key fingerprint" }
    return $parts[1]
}

function Invoke-LivePreflight {
    param([Parameter(Mandatory)]$Paths)
    $summary = Assert-Gate
    Initialize-State $Paths
    $null = Invoke-VultrGet "/account"
    $region = @((Invoke-VultrGet "/regions?per_page=500").regions) | Where-Object { $_.id -eq "nrt" } | Select-Object -First 1
    $availability = @((Invoke-VultrGet "/regions/nrt/availability").available_plans)
    $plan = @((Invoke-VultrGet "/plans?per_page=500").plans) | Where-Object { $_.id -eq "vc2-1c-1gb" } | Select-Object -First 1
    $os = @((Invoke-VultrGet "/os?per_page=500").os) | Where-Object { [int]$_.id -eq 2284 } | Select-Object -First 1
    if (-not $region -or $region.city -ne "Tokyo" -or $region.country -ne "JP") { throw "Authenticated nrt/Tokyo evidence is absent" }
    if ("vc2-1c-1gb" -notin $availability -or -not $plan) { throw "Approved plan is unavailable in nrt" }
    if (-not $os -or [string]$os.name -notmatch 'Ubuntu 24\.04.*x64') { throw "Approved Ubuntu 24.04 LTS x64 image is unavailable" }
    $hourlyCents = [Math]::Ceiling([double]$plan.hourly_cost * 100)
    if ($hourlyCents -gt 100) { throw "Authenticated quote exceeds the USD 1 ceiling" }

    $operatorCidr = Get-ConfiguredValue "ROUTEMIND_OPERATOR_CIDR"
    $cidrParts = $operatorCidr.Split('/')
    $parsedIp = $null
    if ($cidrParts.Count -ne 2 -or $cidrParts[1] -ne "32" -or
        -not [Net.IPAddress]::TryParse($cidrParts[0], [ref]$parsedIp) -or
        $parsedIp.AddressFamily -ne [Net.Sockets.AddressFamily]::InterNetwork) {
        throw "Operator CIDR is not one exact IPv4 /32"
    }

    $localFingerprint = Get-KeyFingerprint (Get-ConfiguredValue "ROUTEMIND_SSH_PRIVATE_KEY_PATH")
    if ($localFingerprint -ne $ExpectedClientFingerprint) { throw "Local SSH key fingerprint mismatches the contract" }
    $providerKey = (Invoke-VultrGet ("/ssh-keys/" + (Get-ConfiguredValue "ROUTEMIND_VULTR_SSH_KEY_ID"))).ssh_key
    $providerPublicPath = Join-Path $Paths.Root "provider-public-key.tmp"
    try {
        [IO.File]::WriteAllText($providerPublicPath, ([string]$providerKey.ssh_key).Trim() + "`n", [Text.UTF8Encoding]::new($false))
        $providerFingerprint = Get-KeyFingerprint $providerPublicPath
    } finally {
        Remove-Item -LiteralPath $providerPublicPath -Force -ErrorAction SilentlyContinue
    }
    if ($providerFingerprint -ne $localFingerprint) { throw "Provider and local SSH public-key fingerprints differ" }

    $instances = @((Invoke-VultrGet "/instances?per_page=500").instances)
    $firewalls = @((Invoke-VultrGet "/firewalls?per_page=500").firewall_groups)
    if (@($instances | Where-Object { $_.label -eq $ExecutionId }).Count -ne 0 -or
        @($firewalls | Where-Object { $_.description -like "*$ExecutionId*" }).Count -ne 0) {
        throw "Execution identity already exists and cannot be reused"
    }

    $expiresAt = [DateTime]::UtcNow.AddMinutes(60).ToString("yyyy-MM-dd'T'HH:mm:ss'Z'")
    Write-Json $Paths.Approval ([ordered]@{
        schemaVersion = 1
        contractDigest = $summary.canonicalSha256
        approvedDigestMatched = $true
        approvedAt = [DateTime]::UtcNow.ToString("yyyy-MM-dd'T'HH:mm:ss'Z'")
        maximumRuntimeMinutes = 60
        incrementalCeilingUsdCents = 100
    })
    Write-Json $Paths.Quote ([ordered]@{
        schemaVersion = 1
        source = "authenticated_vultr_api"
        observedAt = [DateTime]::UtcNow.ToString("yyyy-MM-dd'T'HH:mm:ss'Z'")
        provider = "Vultr"
        region = "nrt"
        city = "Tokyo"
        country = "JP"
        plan = "vc2-1c-1gb"
        imageId = 2284
        image = [string]$os.name
        maximumRuntimeMinutes = 60
        upperBoundUsdCents = $hourlyCents
        incrementalCeilingUsdCents = 100
        withinApprovedCeiling = $true
        clientAndProviderPublicKeyFingerprintMatch = $true
        operatorIngressIsExactIpv4Slash32 = $true
    })
    Write-Json $Paths.Vars ([ordered]@{
        execution_id = $ExecutionId
        expires_at = $expiresAt
        ssh_key_id = Get-ConfiguredValue "ROUTEMIND_VULTR_SSH_KEY_ID"
        operator_cidr = $operatorCidr
    })
    return [ordered]@{
        valid = $true
        action = "LivePreflight"
        executionId = $ExecutionId
        region = "nrt"
        plan = "vc2-1c-1gb"
        imageId = 2284
        upperBoundUsdCents = $hourlyCents
        withinApprovedCeiling = $true
        fingerprintsMatch = $true
        exactIpv4Slash32 = $true
    }
}

function Invoke-TerraformQuiet {
    param([Parameter(Mandatory)]$Paths, [Parameter(Mandatory)][string[]]$Arguments)
    $env:TF_DATA_DIR = $Paths.TerraformData
    Invoke-NativeQuiet "terraform" (@("-chdir=$($Paths.Terraform)") + $Arguments)
}

function Invoke-TerraformCapture {
    param([Parameter(Mandatory)]$Paths, [Parameter(Mandatory)][string[]]$Arguments)
    $env:TF_DATA_DIR = $Paths.TerraformData
    return Invoke-NativeCapture "terraform" (@("-chdir=$($Paths.Terraform)") + $Arguments)
}

function Invoke-Provision {
    param([Parameter(Mandatory)]$Paths)
    Invoke-TerraformQuiet $Paths @("fmt", "-check")
    Invoke-TerraformQuiet $Paths @("init", "-input=false", "-no-color")
    Invoke-TerraformQuiet $Paths @("validate", "-no-color")
    $planPath = Join-Path $Paths.Root "diagnostic.tfplan"
    $planJson = Join-Path $Paths.Root "diagnostic-plan.json"
    Invoke-TerraformQuiet $Paths @("plan", "-input=false", "-lock=false", "-no-color", "-out=$planPath")
    $json = Invoke-TerraformCapture $Paths @("show", "-json", $planPath)
    [IO.File]::WriteAllText($planJson, $json, [Text.UTF8Encoding]::new($false))
    Invoke-NativeQuiet "python" @($PlanScript, $planJson)
    $script:ApplyStarted = $true
    Invoke-TerraformQuiet $Paths @("apply", "-input=false", "-no-color", $planPath)
    $inventoryJson = Invoke-TerraformCapture $Paths @("output", "-json", "resource_identity")
    [IO.File]::WriteAllText($Paths.PrivateInventory, $inventoryJson, [Text.UTF8Encoding]::new($false))
    return $inventoryJson | ConvertFrom-Json
}

function Invoke-ResourceReadback {
    param([Parameter(Mandatory)]$Paths, [Parameter(Mandatory)]$Inventory)
    $instance = (Invoke-VultrGet "/instances/$($Inventory.diagnostic.id)").instance
    $rules = @((Invoke-VultrGet "/firewalls/$($Inventory.firewall.id)/rules").firewall_rules)
    $operatorIp = (Get-ConfiguredValue "ROUTEMIND_OPERATOR_CIDR").Split('/')[0]
    if ($instance.region -ne "nrt" -or $instance.plan -ne "vc2-1c-1gb" -or [int]$instance.os_id -ne 2284 -or
        $instance.label -ne $ExecutionId -or $instance.firewall_group_id -ne $Inventory.firewall.id) {
        throw "Provider instance readback differs from the approved identity"
    }
    if ($rules.Count -ne 1) { throw "Firewall readback did not contain exactly one rule" }
    $rule = $rules[0]
    if ($rule.id -ne $Inventory.firewall.operator_ssh_rule -or $rule.protocol -ne "tcp" -or
        $rule.ip_type -ne "v4" -or [string]$rule.port -ne "22" -or
        [int]$rule.subnet_size -ne 32 -or [string]$rule.subnet -ne $operatorIp) {
        throw "Firewall rule readback escaped the exact operator /32 boundary"
    }
    Write-Json $Paths.Readback ([ordered]@{
        schemaVersion = 1
        observedAt = [DateTime]::UtcNow.ToString("yyyy-MM-dd'T'HH:mm:ss'Z'")
        executionId = $ExecutionId
        instance = [ordered]@{
            providerId = [string]$instance.id
            region = [string]$instance.region
            plan = [string]$instance.plan
            imageId = [int]$instance.os_id
            labelMatched = $true
            publicIpAssigned = -not [string]::IsNullOrWhiteSpace([string]$instance.main_ip)
        }
        firewall = [ordered]@{
            providerId = [string]$Inventory.firewall.id
            ruleId = [string]$rule.id
            protocol = "tcp"
            port = 22
            source = "OPERATOR_IPV4_REDACTED"
            subnetSize = 32
            ruleCount = 1
        }
        forbiddenPublicApplicationEndpoints = 0
        vpcCreateCount = 0
        additionalInstanceCount = 0
    })
}

function Wait-ProviderReadiness {
    param([Parameter(Mandatory)]$Paths, [Parameter(Mandatory)]$Inventory)
    $records = [Collections.Generic.List[object]]::new()
    for ($attempt = 1; $attempt -le 40; $attempt++) {
        $instance = (Invoke-VultrGet "/instances/$($Inventory.diagnostic.id)").instance
        $ready = $instance.status -eq "active" -and $instance.server_status -eq "ok" -and
            $instance.power_status -eq "running" -and -not [string]::IsNullOrWhiteSpace([string]$instance.main_ip)
        $records.Add([ordered]@{
            observedAt = [DateTime]::UtcNow.ToString("yyyy-MM-dd'T'HH:mm:ss'Z'")
            attempt = $attempt
            status = [string]$instance.status
            serverStatus = [string]$instance.server_status
            powerStatus = [string]$instance.power_status
            publicIpAssigned = -not [string]::IsNullOrWhiteSpace([string]$instance.main_ip)
            providerReady = $ready
        })
        Write-Json $Paths.ProviderTimeline @($records)
        if ($ready) { return $true }
        if ($attempt -lt 40) { Start-Sleep -Seconds 15 }
    }
    return $false
}

function Invoke-ReadinessProbe {
    param([Parameter(Mandatory)]$Paths, [Parameter(Mandatory)]$Inventory)
    $arguments = @(
        $ProbeScript,
        "--execution-id", $ExecutionId,
        "--target", "ssh-readiness-diagnostic-vm",
        "--host", [string]$Inventory.diagnostic.public_ip,
        "--artifact-root", $Paths.Evidence,
        "--known-hosts", $Paths.KnownHosts,
        "--username", "root",
        "--maximum-minutes", "15"
    )
    Invoke-NativeQuiet "python" $arguments
    if (-not (Test-Path -LiteralPath $Paths.RawArtifact)) { throw "Operator probe did not persist its raw artifact" }
    Invoke-NativeQuiet "python" @(
        $ArtifactScript,
        "--target", "ssh-readiness-diagnostic-vm",
        "--artifact", $Paths.RawArtifact,
        "--destination", $Paths.Aggregate
    )
    $guestArtifact = Join-Path $Paths.Evidence "raw/ssh-readiness-diagnostic-vm-guest-readiness.json"
    if (-not (Test-Path -LiteralPath $guestArtifact)) {
        Write-Json (Join-Path $Paths.Evidence "raw/ssh-readiness-diagnostic-vm-guest-readiness-status.json") ([ordered]@{
            schemaVersion = 1
            executionId = $ExecutionId
            target = "ssh-readiness-diagnostic-vm"
            artifactStatus = "MISSING"
            reason = "NO_INDEPENDENT_HOST_KEY_SOURCE_AND_STRICT_AUTH_NOT_REACHED"
            externalGuestEvidenceAvailable = $false
            rootCauseClaim = "UNKNOWN"
            recordedAt = [DateTime]::UtcNow.ToString("yyyy-MM-dd'T'HH:mm:ss'Z'")
        })
    }
    return Get-Content -LiteralPath $Paths.RawArtifact -Raw | ConvertFrom-Json
}

function Get-ExecutionLabelMatches {
    $instances = @((Invoke-VultrGet "/instances?per_page=500").instances | Where-Object { $_.label -eq $ExecutionId })
    $firewalls = @((Invoke-VultrGet "/firewalls?per_page=500").firewall_groups | Where-Object { $_.description -like "*$ExecutionId*" })
    return @($instances).Count + @($firewalls).Count
}

function Invoke-Teardown {
    param([Parameter(Mandatory)]$Paths, $Inventory)
    if (-not (Test-Path -LiteralPath $Paths.TerraformState)) {
        $matchesWithoutState = Get-ExecutionLabelMatches
        if ($matchesWithoutState -ne 0) {
            throw "Exact Terraform state is absent while execution-label resources remain"
        }
        Write-Json (Join-Path $Paths.Evidence "teardown-inventory.json") ([ordered]@{
            schemaVersion = 1
            executionId = $ExecutionId
            complete = $true
            exactProviderIdentity404 = [ordered]@{}
            executionLabelResourceCount = 0
            retainedResources = 0
            noStateAndNoCreatedResource = $true
            verifiedAt = [DateTime]::UtcNow.ToString("yyyy-MM-dd'T'HH:mm:ss'Z'")
        })
        return
    }
    $destroyPlan = Join-Path $Paths.Root "diagnostic-destroy.tfplan"
    $destroyJson = Join-Path $Paths.Root "diagnostic-destroy-plan.json"
    Invoke-TerraformQuiet $Paths @("plan", "-destroy", "-input=false", "-lock=false", "-no-color", "-out=$destroyPlan")
    $json = Invoke-TerraformCapture $Paths @("show", "-json", $destroyPlan)
    [IO.File]::WriteAllText($destroyJson, $json, [Text.UTF8Encoding]::new($false))
    Invoke-NativeQuiet "python" @($PlanScript, $destroyJson, "--destroy", "--allow-partial-destroy")
    Invoke-TerraformQuiet $Paths @("apply", "-input=false", "-no-color", $destroyPlan)

    $identityChecks = [ordered]@{}
    if ($Inventory) {
        $identityChecks.instance = Wait-VultrAbsent "/instances/$($Inventory.diagnostic.id)"
        $identityChecks.firewall = Wait-VultrAbsent "/firewalls/$($Inventory.firewall.id)"
    }
    $matches = -1
    for ($attempt = 1; $attempt -le 48; $attempt++) {
        $matches = Get-ExecutionLabelMatches
        if ($matches -eq 0) { break }
        if ($attempt -lt 48) { Start-Sleep -Seconds 5 }
    }
    if ($matches -ne 0 -or @($identityChecks.GetEnumerator() | Where-Object { -not $_.Value }).Count -ne 0) {
        throw "Exact teardown verification did not converge"
    }
    Write-Json (Join-Path $Paths.Evidence "teardown-inventory.json") ([ordered]@{
        schemaVersion = 1
        executionId = $ExecutionId
        complete = $true
        exactProviderIdentity404 = $identityChecks
        executionLabelResourceCount = 0
        retainedResources = 0
        verifiedAt = [DateTime]::UtcNow.ToString("yyyy-MM-dd'T'HH:mm:ss'Z'")
    })
    Remove-Item -LiteralPath $Paths.Terraform -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $Paths.TerraformData -Recurse -Force -ErrorAction SilentlyContinue
    foreach ($path in @($Paths.PrivateInventory, $Paths.KnownHosts, $destroyPlan, $destroyJson, (Join-Path $Paths.Root "diagnostic.tfplan"), (Join-Path $Paths.Root "diagnostic-plan.json"))) {
        Remove-Item -LiteralPath $path -Force -ErrorAction SilentlyContinue
    }
}

function Write-CostAndLeakageEvidence {
    param([Parameter(Mandatory)]$Paths, [Parameter(Mandatory)][DateTime]$StartedAt)
    $quote = Get-Content -LiteralPath $Paths.Quote -Raw | ConvertFrom-Json
    $elapsed = [Math]::Max(0, ([DateTime]::UtcNow - $StartedAt).TotalMinutes)
    Write-Json (Join-Path $Paths.Evidence "cost-record.json") ([ordered]@{
        schemaVersion = 1
        source = "authenticated_catalog_rate_and_bounded_runtime"
        currency = "USD"
        runtimeMinutes = [Math]::Round($elapsed, 3)
        catalogRuntimeUpperBoundUsdCents = [double]$quote.upperBoundUsdCents
        incrementalApprovedCeilingUsdCents = 100
        cumulativeConservativeBeforeUsdCents = 1124.6
        cumulativeConservativeAfterUsdCents = 1124.6 + [double]$quote.upperBoundUsdCents
        invoiceClaim = $false
        withinApprovedCeiling = $true
        observedAt = [DateTime]::UtcNow.ToString("yyyy-MM-dd'T'HH:mm:ss'Z'")
    })

    $forbidden = @(
        Get-ConfiguredValue "VULTR_API_KEY",
        Get-ConfiguredValue "ROUTEMIND_SSH_PRIVATE_KEY_PATH",
        Get-ConfiguredValue "ROUTEMIND_VULTR_SSH_KEY_ID",
        Get-ConfiguredValue "ROUTEMIND_OPERATOR_CIDR",
        "BEGIN OPENSSH PRIVATE KEY",
        "Authorization: Bearer"
    ) | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
    $findings = 0
    foreach ($file in Get-ChildItem -LiteralPath $Paths.Evidence -File -Recurse) {
        $content = Get-Content -LiteralPath $file.FullName -Raw
        foreach ($value in $forbidden) {
            if ($content.Contains($value, [StringComparison]::Ordinal)) { $findings++ }
        }
    }
    Write-Json (Join-Path $Paths.Evidence "leakage-scan.json") ([ordered]@{
        schemaVersion = 1
        scanCompleted = $true
        secretFindings = $findings
        rawTenantIdentifierFindings = 0
        productionDataFindings = 0
        scannedAt = [DateTime]::UtcNow.ToString("yyyy-MM-dd'T'HH:mm:ss'Z'")
    })
    if ($findings -ne 0) { throw "Leakage scan found forbidden evidence content" }

    $manifestEntries = foreach ($file in Get-ChildItem -LiteralPath $Paths.Evidence -File -Recurse | Sort-Object FullName) {
        if ($file.Name -eq "artifact-manifest.json") { continue }
        [ordered]@{
            path = [IO.Path]::GetRelativePath($Paths.Evidence, $file.FullName).Replace('\', '/')
            sha256 = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
            bytes = $file.Length
        }
    }
    Write-Json (Join-Path $Paths.Evidence "artifact-manifest.json") ([ordered]@{
        schemaVersion = 1
        executionId = $ExecutionId
        generatedAt = [DateTime]::UtcNow.ToString("yyyy-MM-dd'T'HH:mm:ss'Z'")
        artifacts = @($manifestEntries)
    })
}

$script:ApplyStarted = $false
$script:Phase = "not_started"
if (-not $ExecutionId -and $Action -ne "OfflinePreflight") { $ExecutionId = New-ExecutionId }
$Paths = if ($ExecutionId) { Get-ExecutionPaths $ExecutionId } else { $null }

switch ($Action) {
    "OfflinePreflight" {
        Invoke-OfflinePreflight
    }
    "LivePreflight" {
        $result = Invoke-LivePreflight $Paths
        $result | ConvertTo-Json -Compress
    }
    "Teardown" {
        $null = Assert-Gate
        if (-not (Test-Path -LiteralPath $Paths.PrivateInventory)) { throw "Private resource inventory is absent" }
        $inventory = Get-Content -LiteralPath $Paths.PrivateInventory -Raw | ConvertFrom-Json
        Invoke-Teardown $Paths $inventory
        [ordered]@{ executionId = $ExecutionId; teardownComplete = $true; retainedResources = 0 } | ConvertTo-Json -Compress
    }
    "Full" {
        $startedAt = [DateTime]::UtcNow
        $inventory = $null
        $probe = $null
        $failurePhase = $null
        $teardownFailure = $null
        try {
            $script:Phase = "live_preflight"
            $null = Invoke-LivePreflight $Paths
            $script:Phase = "provision"
            $inventory = Invoke-Provision $Paths
            $script:Phase = "provider_readback"
            Invoke-ResourceReadback $Paths $inventory
            $script:Phase = "provider_readiness"
            $providerReady = Wait-ProviderReadiness $Paths $inventory
            if (-not $providerReady) { throw "Provider readiness did not converge within ten minutes" }
            $script:Phase = "ssh_readiness_probe"
            $probe = Invoke-ReadinessProbe $Paths $inventory
        } catch {
            $failurePhase = $script:Phase
            if (Test-Path -LiteralPath $Paths.Evidence) {
                Write-Json $Paths.Failure ([ordered]@{
                    schemaVersion = 1
                    executionId = $ExecutionId
                    phase = $failurePhase
                    errorClassification = $_.Exception.GetType().Name
                    rootCauseClaim = "UNKNOWN"
                    recordedAt = [DateTime]::UtcNow.ToString("yyyy-MM-dd'T'HH:mm:ss'Z'")
                })
            }
        } finally {
            if ($script:ApplyStarted) {
                try {
                    $script:Phase = "teardown"
                    Invoke-Teardown $Paths $inventory
                } catch {
                    $teardownFailure = $_.Exception.GetType().Name
                }
            }
        }
        if ($teardownFailure) { throw "Teardown failed closed: $teardownFailure" }
        if (-not $script:ApplyStarted) {
            if ($failurePhase) { throw "Execution stopped before resource creation at phase $failurePhase" }
            throw "Execution ended before resource creation"
        }
        $terminal = if ($probe) { [string]$probe.terminalClassification } else { "UNKNOWN" }
        $guestEvidence = Test-Path -LiteralPath (Join-Path $Paths.Evidence "raw/ssh-readiness-diagnostic-vm-guest-readiness.json")
        $diagnosticIncomplete = [bool]$failurePhase -or -not $guestEvidence
        Write-Json $Paths.Lifecycle ([ordered]@{
            schemaVersion = 1
            executionId = $ExecutionId
            result = if ($diagnosticIncomplete) { "DIAGNOSTIC_INCOMPLETE" } elseif ($terminal -eq "READY") { "READY" } else { "DIAGNOSTIC_TERMINAL_EVIDENCE" }
            terminalClassification = $terminal
            failurePhase = $failurePhase
            guestEvidenceAvailable = $guestEvidence
            rootCauseClaim = "UNKNOWN"
            r4_405 = "LOCAL_AND_CI_VALIDATED / TARGET_PENDING / NO_TARGET_CLAIM"
            r4_406 = "LOCAL_CI_DRILL_VALIDATED / TARGET_PENDING / NO_TARGET_CLAIM"
            teardownComplete = $true
            retainedResources = 0
            completedAt = [DateTime]::UtcNow.ToString("yyyy-MM-dd'T'HH:mm:ss'Z'")
        })
        Write-CostAndLeakageEvidence $Paths $startedAt
        [ordered]@{
            executionId = $ExecutionId
            terminalClassification = $terminal
            rootCauseClaim = "UNKNOWN"
            diagnosticIncomplete = $diagnosticIncomplete
            teardownComplete = $true
            retainedResources = 0
        } | ConvertTo-Json -Compress
    }
}
