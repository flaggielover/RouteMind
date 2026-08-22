[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$required = @(
    "AGENTS.md",
    "MASTER_SPEC.md",
    "MASTER_ARCHITECTURE.md",
    "ROADMAP.md",
    "TASK_GRAPH.yaml",
    "PROGRESS.md",
    "HANDOFF.md",
    "QUALITY_GATES.md",
    "DECISIONS.md"
)

Push-Location $root
try {
    $missing = @($required | Where-Object { -not (Test-Path -LiteralPath $_ -PathType Leaf) })
    if ($missing.Count -gt 0) {
        throw "Missing required control files: $($missing -join ', ')"
    }

    python scripts/validate_control_plane.py
    if ($LASTEXITCODE -ne 0) {
        throw "Task graph validation failed"
    }

    python scripts/security_gate.py
    if ($LASTEXITCODE -ne 0) {
        throw "Security and supply-chain hygiene gate failed"
    }

    python scripts/security_gate_test.py
    if ($LASTEXITCODE -ne 0) {
        throw "Security gate self-tests failed"
    }

    python scripts/recovery_contract_test.py
    if ($LASTEXITCODE -ne 0) {
        throw "Recovery contract self-tests failed"
    }

    python scripts/release_contract_test.py
    if ($LASTEXITCODE -ne 0) {
        throw "Release contract self-tests failed"
    }

    python scripts/staged_release_test.py
    if ($LASTEXITCODE -ne 0) {
        throw "Staged release self-tests failed"
    }

    if (Test-Path -LiteralPath "compose.yaml") {
        if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
            throw "Docker is required to validate compose.yaml"
        }
        docker compose config --quiet
        if ($LASTEXITCODE -ne 0) {
            throw "Compose configuration validation failed"
        }
        Write-Host "PASS: Compose configuration"
    }

    $scripts = Get-ChildItem -LiteralPath scripts -Filter "*.ps1"
    foreach ($script in $scripts) {
        $tokens = $null
        $errors = $null
        [void][System.Management.Automation.Language.Parser]::ParseFile(
            $script.FullName,
            [ref]$tokens,
            [ref]$errors
        )
        if ($errors.Count -gt 0) {
            throw "PowerShell parse failure in $($script.Name): $($errors -join '; ')"
        }
    }

    Write-Host "PASS: required control files"
    Write-Host "PASS: PowerShell script syntax"
    Write-Host "PASS: RouteMind fast repository gate"
}
finally {
    Pop-Location
}
