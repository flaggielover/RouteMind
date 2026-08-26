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

    python scripts/validate_control_plane_test.py
    if ($LASTEXITCODE -ne 0) {
        throw "Task graph validator self-tests failed"
    }

    python scripts/negative_results_gate.py
    if ($LASTEXITCODE -ne 0) {
        throw "Negative-results append-only audit failed"
    }

    python scripts/negative_results_gate_test.py
    if ($LASTEXITCODE -ne 0) {
        throw "Negative-results gate self-tests failed"
    }

    python scripts/claim_matrix_gate.py
    if ($LASTEXITCODE -ne 0) {
        throw "Final claim matrix gate failed"
    }

    python scripts/claim_matrix_gate_test.py
    if ($LASTEXITCODE -ne 0) {
        throw "Final claim matrix gate self-tests failed"
    }

    python scripts/final_scientific_figures.py
    if ($LASTEXITCODE -ne 0) {
        throw "Final scientific figures gate failed"
    }

    python scripts/final_scientific_figures_test.py
    if ($LASTEXITCODE -ne 0) {
        throw "Final scientific figures self-tests failed"
    }

    python scripts/round4_graph_gate.py
    if ($LASTEXITCODE -ne 0) {
        throw "Prepared Round 4 task graph gate failed"
    }

    python scripts/round4_graph_gate_test.py
    if ($LASTEXITCODE -ne 0) {
        throw "Prepared Round 4 task graph self-tests failed"
    }

    python scripts/security_gate.py
    if ($LASTEXITCODE -ne 0) {
        throw "Security and supply-chain hygiene gate failed"
    }

    python scripts/security_gate_test.py
    if ($LASTEXITCODE -ne 0) {
        throw "Security gate self-tests failed"
    }

    python scripts/supply_chain_evidence_test.py
    if ($LASTEXITCODE -ne 0) {
        throw "Supply-chain evidence self-tests failed"
    }

    python scripts/deployment_contract.py
    if ($LASTEXITCODE -ne 0) {
        throw "Deployment target contract validation failed"
    }

    python scripts/deployment_contract_test.py
    if ($LASTEXITCODE -ne 0) {
        throw "Deployment target contract self-tests failed"
    }

    python scripts/telemetry_export_contract.py
    if ($LASTEXITCODE -ne 0) {
        throw "Telemetry export contract validation failed"
    }

    python scripts/telemetry_export_contract_test.py
    if ($LASTEXITCODE -ne 0) {
        throw "Telemetry export contract self-tests failed"
    }

    python scripts/r4_external_validation.py
    if ($LASTEXITCODE -ne 0) {
        throw "Vultr Tokyo external-validation preparation contract failed"
    }

    python scripts/r4_external_validation_test.py
    if ($LASTEXITCODE -ne 0) {
        throw "Vultr Tokyo external-validation contract self-tests failed"
    }

    python scripts/path_safety_test.py
    if ($LASTEXITCODE -ne 0) {
        throw "External-validation path safety self-tests failed"
    }

    python scripts/r4_tls_identities_test.py
    if ($LASTEXITCODE -ne 0) {
        throw "External-validation TLS identity self-tests failed"
    }

    python scripts/r4_kube_endpoint_test.py
    if ($LASTEXITCODE -ne 0) {
        throw "External-validation Kubernetes endpoint self-tests failed"
    }

    python scripts/r4_controller_guard_test.py
    if ($LASTEXITCODE -ne 0) {
        throw "External-validation controller guard self-tests failed"
    }

    python scripts/r4_external_evidence_test.py
    if ($LASTEXITCODE -ne 0) {
        throw "Vultr Tokyo external-evidence assembler self-tests failed"
    }

    python scripts/product_contract.py
    if ($LASTEXITCODE -ne 0) {
        throw "Product semantics contract validation failed"
    }

    python scripts/product_contract_test.py
    if ($LASTEXITCODE -ne 0) {
        throw "Product semantics contract self-tests failed"
    }

    python scripts/agent_policy.py
    if ($LASTEXITCODE -ne 0) {
        throw "Agent authority policy validation failed"
    }

    python scripts/agent_policy_test.py
    if ($LASTEXITCODE -ne 0) {
        throw "Agent authority policy self-tests failed"
    }

    python scripts/recovery_contract_test.py
    if ($LASTEXITCODE -ne 0) {
        throw "Recovery contract self-tests failed"
    }

    python scripts/disaster_recovery_test.py
    if ($LASTEXITCODE -ne 0) {
        throw "Disaster recovery evidence self-tests failed"
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
