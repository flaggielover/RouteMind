[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$IacRoot = Join-Path $RepoRoot "infra/external-validation/vultr-tokyo-vm-v2"
$RuntimeRoot = Join-Path $RepoRoot "infra/external-validation/vultr-tokyo-vm"
$TempRoot = Join-Path ([IO.Path]::GetTempPath()) ("routemind-r4-vm-v2-gate-" + [Guid]::NewGuid().ToString("N"))

function Invoke-Checked {
    param([string]$Command, [string[]]$Arguments)
    & $Command @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Command failed with exit code $LASTEXITCODE"
    }
}

try {
    Push-Location $RepoRoot
    Invoke-Checked "python" @("scripts/r4_vm_external_validation_v2.py")

    if (-not (Get-Command terraform -ErrorAction SilentlyContinue)) {
        throw "Terraform is required for the VM v2 external-validation offline gate"
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

    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        throw "Docker Compose is required for the VM v2 external-validation offline gate"
    }
    $SecretRoot = Join-Path $TempRoot "secrets"
    New-Item -ItemType Directory -Path (Join-Path $SecretRoot "tls") -Force | Out-Null
    foreach ($name in @("postgres-password", "rabbitmq-password", "redis-password", "telemetry-attribution-key")) {
        Set-Content -LiteralPath (Join-Path $SecretRoot $name) -Value "offline-validation-placeholder" -NoNewline
    }
    $previousSecretRoot = $env:ROUTEMIND_SECRET_ROOT
    $previousRevision = $env:ROUTEMIND_SOURCE_REVISION
    try {
        $env:ROUTEMIND_SECRET_ROOT = $SecretRoot
        $env:ROUTEMIND_SOURCE_REVISION = "0000000000000000000000000000000000000000"
        Invoke-Checked "docker" @("compose", "-f", (Join-Path $RuntimeRoot "routemind-compose.yaml"), "config", "--quiet")
    }
    finally {
        $env:ROUTEMIND_SECRET_ROOT = $previousSecretRoot
        $env:ROUTEMIND_SOURCE_REVISION = $previousRevision
    }
    & (Join-Path $RepoRoot "scripts/r4_vm_foundry_gate.ps1")
    if ($LASTEXITCODE -ne 0) {
        throw "Pinned SigNoz Foundry gate failed"
    }
    Write-Host "PASS: RouteMind Tokyo no-new-VPC VM v2 offline gate"
}
finally {
    Pop-Location -ErrorAction SilentlyContinue
    if (Test-Path -LiteralPath $TempRoot) {
        Remove-Item -LiteralPath $TempRoot -Recurse -Force
    }
}
