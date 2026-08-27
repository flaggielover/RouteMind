[CmdletBinding()]
param(
    [switch]$VerifyLocalKey
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$IacRoot = Join-Path $RepoRoot "infra/external-validation/vultr-tokyo-vm-ssh-readiness-v1"
$ContractPath = Join-Path $RepoRoot "contracts/external-validation/r4-vultr-tokyo-vm-ssh-readiness-diagnostic-v1.json"
$TempRoot = Join-Path ([IO.Path]::GetTempPath()) ("routemind-r4-ssh-readiness-gate-" + [Guid]::NewGuid().ToString("N"))
$ExpectedFingerprint = "SHA256:JHiQkjaVyp5ft91S12iyyCbDB6PCAGhDqYTVnMJAUeI"

function Invoke-Checked {
    param([string]$Command, [string[]]$Arguments)
    & $Command @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Command failed with exit code $LASTEXITCODE"
    }
}

function Resolve-ConfigurationValue {
    param([string]$Name)
    $value = [Environment]::GetEnvironmentVariable($Name, "Process")
    if ([string]::IsNullOrWhiteSpace($value)) {
        $value = [Environment]::GetEnvironmentVariable($Name, "User")
    }
    return $value
}

function Assert-NoCaseAmbiguousKeys {
    param([object]$Value, [string]$Path = '$')
    if ($Value -is [Collections.IDictionary]) {
        $seen = @{}
        foreach ($key in $Value.Keys) {
            $folded = ([string]$key).ToLowerInvariant()
            if ($seen.ContainsKey($folded)) {
                throw "Case-ambiguous JSON key at $Path"
            }
            $seen[$folded] = $true
            Assert-NoCaseAmbiguousKeys -Value $Value[$key] -Path "$Path.$key"
        }
    }
    elseif ($Value -is [Collections.IEnumerable] -and $Value -isnot [string]) {
        $index = 0
        foreach ($item in $Value) {
            Assert-NoCaseAmbiguousKeys -Value $item -Path "$Path[$index]"
            $index++
        }
    }
}

try {
    Push-Location $RepoRoot
    Invoke-Checked "python" @("scripts/r4_vm_ssh_readiness_contract.py")
    Invoke-Checked "python" @("scripts/r4_vm_ssh_readiness_contract_test.py")
    Invoke-Checked "python" @("scripts/r4_ssh_readiness_test.py")
    Invoke-Checked "python" @("scripts/r4_vm_ssh_readiness_probe_test.py")
    Invoke-Checked "python" @("scripts/r4_vm_ssh_readiness_plan_test.py")
    Invoke-Checked "python" @("scripts/r4_vm_ssh_readiness_controller_test.py")

    $contract = Get-Content -LiteralPath $ContractPath -Raw | ConvertFrom-Json -AsHashtable
    Assert-NoCaseAmbiguousKeys -Value $contract

    if ($VerifyLocalKey) {
        $keyPathValue = Resolve-ConfigurationValue "ROUTEMIND_SSH_PRIVATE_KEY_PATH"
        if ([string]::IsNullOrWhiteSpace($keyPathValue)) {
            throw "ROUTEMIND_SSH_PRIVATE_KEY_PATH is missing"
        }
        $previousPath = $env:ROUTEMIND_SSH_PRIVATE_KEY_PATH
        try {
            $env:ROUTEMIND_SSH_PRIVATE_KEY_PATH = $keyPathValue
            Invoke-Checked "python" @(
                "scripts/path_safety.py",
                "--root", $RepoRoot,
                "--candidate-env", "ROUTEMIND_SSH_PRIVATE_KEY_PATH"
            )
        }
        finally {
            $env:ROUTEMIND_SSH_PRIVATE_KEY_PATH = $previousPath
        }
        $keyPath = [IO.Path]::GetFullPath($keyPathValue)
        if (-not (Test-Path -LiteralPath $keyPath -PathType Leaf)) {
            throw "Configured SSH private-key file is missing"
        }
        $fingerprintOutput = @(& ssh-keygen -lf $keyPath -E sha256 2>$null)
        if ($LASTEXITCODE -ne 0 -or $fingerprintOutput.Count -ne 1) {
            throw "Unable to calculate the local public-key fingerprint"
        }
        $parts = $fingerprintOutput[0] -split '\s+'
        if ($parts.Count -lt 4 -or $parts[1] -ne $ExpectedFingerprint -or $parts[-1] -ne "(ED25519)") {
            throw "Local public-key fingerprint does not match the frozen contract"
        }
        foreach ($name in @("ROUTEMIND_VULTR_SSH_KEY_ID", "ROUTEMIND_OPERATOR_CIDR")) {
            if ([string]::IsNullOrWhiteSpace((Resolve-ConfigurationValue $name))) {
                throw "$name is missing"
            }
        }
    }

    if (-not (Get-Command terraform -ErrorAction SilentlyContinue)) {
        throw "Terraform is required for the SSH-readiness offline gate"
    }
    Invoke-Checked "terraform" @("fmt", "-check", $IacRoot)

    New-Item -ItemType Directory -Path $TempRoot | Out-Null
    $TerraformRoot = Join-Path $TempRoot "terraform"
    New-Item -ItemType Directory -Path $TerraformRoot | Out-Null
    foreach ($name in @("versions.tf", "variables.tf", "main.tf", "outputs.tf", "cloud-init.yaml.tftpl")) {
        Copy-Item -LiteralPath (Join-Path $IacRoot $name) -Destination $TerraformRoot
    }
    Invoke-Checked "terraform" @("-chdir=$TerraformRoot", "init", "-backend=false", "-input=false", "-no-color")
    Invoke-Checked "terraform" @("-chdir=$TerraformRoot", "validate", "-no-color")

    $tfvars = [ordered]@{
        execution_id = "r4-vm-ssh-v1-20260827t120000z-abcdef0"
        expires_at = "2026-08-27T13:00:00Z"
        ssh_key_id = "offline-public-key-id"
        operator_cidr = "203.0.113.9/32"
    } | ConvertTo-Json
    [IO.File]::WriteAllText((Join-Path $TerraformRoot "offline.auto.tfvars.json"), $tfvars, [Text.UTF8Encoding]::new($false))
    $previousApiKey = $env:VULTR_API_KEY
    try {
        $env:VULTR_API_KEY = "offline-placeholder-no-provider-call"
        Invoke-Checked "terraform" @(
            "-chdir=$TerraformRoot", "plan", "-refresh=false", "-input=false", "-lock=false",
            "-no-color", "-out=offline.tfplan"
        )
    }
    finally {
        $env:VULTR_API_KEY = $previousApiKey
    }
    $planJson = & terraform "-chdir=$TerraformRoot" show -json offline.tfplan
    if ($LASTEXITCODE -ne 0) {
        throw "terraform show failed"
    }
    $planPath = Join-Path $TempRoot "offline-plan.json"
    [IO.File]::WriteAllText($planPath, ($planJson -join [Environment]::NewLine), [Text.UTF8Encoding]::new($false))
    Invoke-Checked "python" @("scripts/r4_vm_ssh_readiness_plan.py", $planPath)
    Write-Host "PASS: RouteMind Tokyo VM SSH-readiness offline/no-apply gate"
}
finally {
    Pop-Location -ErrorAction SilentlyContinue
    if (Test-Path -LiteralPath $TempRoot) {
        Remove-Item -LiteralPath $TempRoot -Recurse -Force
    }
}
