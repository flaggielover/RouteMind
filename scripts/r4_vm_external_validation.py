from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = (
    ROOT
    / "contracts"
    / "external-validation"
    / "r4-vultr-tokyo-vm-external-validation-v1.json"
)
IAC_ROOT = ROOT / "infra" / "external-validation" / "vultr-tokyo-vm"
DEPLOYMENT_CONTRACT_PATH = (
    ROOT / "contracts" / "deployment" / "r4-401-vultr-tokyo-v1.json"
)

EXPECTED_TASKS = {"R4-405", "R4-406"}
EXPECTED_RECOMPUTE = {"R4-407", "R4-408", "R4-409", "R4-430", "R4-451"}
EXPECTED_PLANS = {"primary-validation-vm": "vc2-8c-32gb", "recovery-validation-vm": "vc2-2c-4gb"}
EXPECTED_TERRAFORM_TYPES = Counter(
    {
        "vultr_firewall_group": 1,
        "vultr_firewall_rule": 2,
        "vultr_instance": 2,
        "vultr_vpc": 1,
    }
)
EXPECTED_DEFERRED_VKE = {
    "vke_control_plane_tls_and_api",
    "kubernetes_network_policy",
    "kubernetes_metrics_api",
    "pvc_csi_reclaim",
    "pod_anti_affinity_and_worker_failure_domain",
    "managed_control_plane_ha",
    "kubernetes_rollout_and_namespace_isolation",
}
EXPECTED_BOUNDARIES = {"http", "messaging", "worker", "simulation", "experiment"}
EXPECTED_SIGNALS = {"traces", "metrics", "logs"}
EXPECTED_COMPONENTS = {
    "business-api",
    "compute-api",
    "PostgreSQL",
    "RabbitMQ",
    "Redis",
    "Outbox relay",
}
EXPECTED_CHECKS = {
    "vultr_tokyo_vm_vpc_firewall_identity",
    "actual_routemind_workload",
    "collector_health",
    "otlp_mtls_connectivity",
    "five_boundary_trace",
    "metrics_export",
    "log_correlation",
    "tenant_security_boundary",
    "cardinality_cost_attribution",
    "leakage_scan",
    "network_failure",
    "collector_outage",
    "backend_outage",
    "export_recovery",
    "durable_business_truth",
    "cross_vm_backup_restore",
    "outbox_inbox_rabbitmq_redis_reconciliation",
    "tenant_audit_rollback_continuity",
    "resource_consumption",
    "cost_accounting",
    "cleanup",
}
EXPECTED_ARTIFACTS = {
    "authenticated-resource-manifest",
    "environment-version-manifest",
    "network-firewall-readback",
    "collector-health",
    "actual-routemind-workload",
    "trace-query",
    "metric-query",
    "correlated-log-query",
    "tenant-cardinality-report",
    "failure-recovery-timeline",
    "target-recovery-report",
    "resource-usage",
    "cost-bound",
    "leakage-scan",
    "cleanup-inventory",
    "artifact-manifest",
}
SHA256 = re.compile(r"^[0-9a-f]{64}$")


class VmExternalValidationError(ValueError):
    pass


def load_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise VmExternalValidationError(f"cannot load JSON object: {path}") from exc
    if not isinstance(value, dict):
        raise VmExternalValidationError(f"JSON root must be an object: {path}")
    return value


def canonical_digest(value: Mapping[str, Any]) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def byte_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def validate_contract(
    contract: Mapping[str, Any], deployment: Mapping[str, Any]
) -> tuple[str, ...]:
    findings: list[str] = []
    if (
        contract.get("schemaVersion") != 1
        or contract.get("contractId") != "r4-vultr-tokyo-vm-external-validation-v1"
        or contract.get("status") != "PREPARED_VM_EXTERNAL_EXECUTION_HUMAN_GATE"
    ):
        findings.append("identity")

    scope = _mapping(contract.get("scope"))
    if (
        set(scope.get("qualificationTasks", [])) != EXPECTED_TASKS
        or set(scope.get("recomputeAfterQualification", [])) != EXPECTED_RECOMPUTE
        or scope.get("productionDeploymentClaimed") is not False
        or scope.get("externalValidationExecuted") is not False
        or scope.get("paidResourcesCreated") is not False
    ):
        findings.append("scope")

    freeze = _mapping(contract.get("vkeDiagnosticFreeze"))
    if (
        freeze.get("status") != "EXTERNAL_VKE_VALIDATION_INCONCLUSIVE"
        or freeze.get("r4_405") != "TARGET_PENDING"
        or freeze.get("r4_406") != "TARGET_PENDING"
        or freeze.get("targetClaim") != "NO_TARGET_CLAIM"
        or freeze.get("rootCauseClaim") != "NO_ROOT_CAUSE_CLAIM"
        or freeze.get("automaticV4Allowed") is not False
        or freeze.get("historicalAttemptsImmutable") is not True
        or freeze.get("preservedAttemptVersions") != ["v1", "v2", "v3"]
        or set(freeze.get("preservedEvidenceClasses", []))
        != {"attempt", "failure", "cost", "teardown"}
    ):
        findings.append("vke_freeze")

    audit = _mapping(contract.get("evidenceContractAudit"))
    deferred = audit.get("deferredVke", [])
    deferred_ids = {
        item.get("id")
        for item in deferred
        if isinstance(item, Mapping) and item.get("disposition") == "DEFERRED_VKE"
    }
    semantics = _mapping(audit.get("closureSemantics"))
    if (
        deferred_ids != EXPECTED_DEFERRED_VKE
        or len(deferred) != len(EXPECTED_DEFERRED_VKE)
        or semantics.get("vmEvidenceMayQualifyPlatformNeutralR4_405AndR4_406Properties")
        is not True
        or semantics.get("vmEvidenceMayClaimVkeValidation") is not False
        or semantics.get("vmEvidenceMayClaimProductionDeployment") is not False
        or semantics.get("deferredVkeItemsMayBeMarkedPassed") is not False
    ):
        findings.append("platform_audit")

    approval = _mapping(contract.get("approvalBoundary"))
    deployment_approval = _mapping(deployment.get("approval"))
    deployment_target = _mapping(deployment.get("target"))
    if (
        approval.get("providerAndResidencyApproved") is not True
        or approval.get("provider") != "Vultr"
        or approval.get("region") != "nrt"
        or approval.get("dataResidency") != "Tokyo, Japan"
        or approval.get("requiredFinalGate")
        != "ROUTEMIND TOKYO VM EXTERNAL VALIDATION HUMAN GATE"
        or approval.get("approvalDigestEnvironmentVariable")
        != "ROUTEMIND_VM_EXTERNAL_EXECUTION_APPROVAL_DIGEST"
        or any(
            approval.get(field) is not False
            for field in (
                "resourceCreationAuthorized",
                "spendAuthorized",
                "liveMutationCallsAuthorized",
            )
        )
        or deployment_approval.get("provider") != approval.get("provider")
        or deployment_target.get("regionId") != approval.get("region")
        or deployment_approval.get("dataResidency") != approval.get("dataResidency")
    ):
        findings.append("approval_boundary")

    backend = _mapping(contract.get("backendDecision"))
    pinned = _mapping(backend.get("pinnedArtifacts"))
    backend_security = _mapping(backend.get("backendSecurity"))
    if (
        backend.get("selected") != "self-hosted-signoz-foundry-compose"
        or backend.get("selectionStatus") != "PREPARED_NOT_DEPLOYED"
        or pinned.get("foundryVersion") != "v0.2.17"
        or SHA256.fullmatch(str(pinned.get("foundryLinuxAmd64Sha256", ""))) is None
        or pinned.get("signozVersion") != "v0.139.0"
        or pinned.get("otelCollectorContribVersion") != "0.159.0"
        or pinned.get("runtimeImageDigestResolutionRequiredBeforeDeploy") is not True
        or pinned.get("mutableLatestTagsAllowedAtDeploy") is not False
        or any(
            backend_security.get(field) is not True
            for field in (
                "metastoreCredentialGeneratedAtExecution",
                "clickHouseCredentialGeneratedAtExecution",
                "credentialsInjectedFromAclRestrictedSecretFiles",
                "foundryProductTelemetryDisabledOrEgressBlockedBeforeTargetForge",
                "deploymentMustFailIfCredentialOrTelemetryControlCannotBeVerified",
            )
        )
        or backend_security.get("directBackendPortsPublished") is not False
        or set(backend_security.get("foundryInvocationRequiredFlags", []))
        != {"--no-ledger", "--no-updater"}
        or backend_security.get("signozAnalyticsEnabled") is not False
        or backend_security.get("signozStatsReporterEnabled") is not False
        or backend_security.get("signozStatsReporterIdentityCollectionEnabled") is not False
    ):
        findings.append("backend")

    infrastructure = _mapping(contract.get("infrastructure"))
    resources = infrastructure.get("resources", [])
    by_id = {
        str(item.get("id")): item for item in resources if isinstance(item, Mapping)
    }
    actual_plans = {key: _mapping(by_id.get(key)).get("plan") for key in EXPECTED_PLANS}
    terraform_counts = Counter(_mapping(infrastructure.get("terraformResourceCounts")))
    if (
        actual_plans != EXPECTED_PLANS
        or _mapping(by_id.get("validation-vpc")).get("cidr") != "10.77.0.0/24"
        or any(_mapping(item).get("region") != "nrt" for item in resources)
        or terraform_counts != EXPECTED_TERRAFORM_TYPES
        or infrastructure.get("publicLoadBalancers") != 0
        or infrastructure.get("blockStorageVolumes") != 0
        or infrastructure.get("vkeClusters") != 0
        or infrastructure.get("publicApplicationIngress") is not False
        or infrastructure.get("providerAutomaticBackups") is not False
        or infrastructure.get("maximumRuntimeHours") != 6
    ):
        findings.append("infrastructure")

    network = _mapping(contract.get("network"))
    public_rules = network.get("publicIngressRules", [])
    private_rules = network.get("privateIngressRules", [])
    if (
        public_rules
        != [{"protocol": "tcp", "port": 22, "source": "ROUTEMIND_OPERATOR_CIDR", "subnetSize": 32}]
        or len(private_rules) != 1
        or _mapping(private_rules[0]).get("source") != "10.77.0.0/24"
        or set(network.get("forbiddenPublicCidrs", [])) != {"0.0.0.0/0", "::/0"}
        or network.get("publishedApplicationPorts") != 0
        or network.get("publishedOtlpPorts") != 0
        or not str(network.get("signozUi", "")).startswith("127.0.0.1:8080")
    ):
        findings.append("network")

    topology = _mapping(contract.get("telemetryTopology"))
    tls = _mapping(topology.get("tls"))
    if (
        set(topology.get("signals", [])) != EXPECTED_SIGNALS
        or not str(topology.get("logSource", "")).startswith("read-only shared application log volume")
        or set(topology.get("requiredCorrelationBoundaries", [])) != EXPECTED_BOUNDARIES
        or topology.get("gatewayPersistentQueue") is not True
        or topology.get("gatewayPersistentQueueMaximumGiB") != 10
        or any(
            tls.get(field) is not True
            for field in (
                "applicationToGatewayMutualTls",
                "gatewayToBackendIngressMutualTls",
                "certificateSanValidationRequired",
                "ephemeralPrivateCa",
            )
        )
        or tls.get("publicPlaintextAllowed") is not False
        or tls.get("privateKeysPersistedAfterCleanup") is not False
    ):
        findings.append("telemetry_topology")

    workload = _mapping(contract.get("workload"))
    if (
        set(workload.get("actualComponents", [])) != EXPECTED_COMPONENTS
        or workload.get("dataClass") != "SYNTHETIC_NO_CUSTOMER_DATA"
        or workload.get("productionTrafficAllowed") is not False
        or workload.get("productionDataAllowed") is not False
        or workload.get("sourceRevisionMustEqualApprovedHead") is not True
    ):
        findings.append("workload")

    secrets = _mapping(contract.get("secretHandling"))
    if (
        set(secrets.get("userConfiguredSecretNames", []))
        != {"VULTR_API_KEY", "ROUTEMIND_SSH_PRIVATE_KEY_PATH"}
        or set(secrets.get("userConfiguredNonSecretNames", []))
        != {"ROUTEMIND_VULTR_SSH_KEY_ID", "ROUTEMIND_OPERATOR_CIDR"}
        or secrets.get("secretValueLoggingAllowed") is not False
        or secrets.get("generatedSecretsDestroyedDuringCleanup") is not True
    ):
        findings.append("secret_handling")

    governance = _mapping(contract.get("dataGovernance"))
    if (
        governance.get("payloadResidency") != "Vultr nrt only"
        or governance.get("rawTelemetryRetentionMaximumHours") != 6
        or governance.get("encryptedRecoveryPackageDeletedBeforeTeardown") is not True
        or governance.get("backendVolumesDeletedBeforeVmTeardown") is not True
    ):
        findings.append("data_governance")

    cost = _mapping(contract.get("cost"))
    if (
        cost.get("primaryHourlyUsdCents") != 21.9
        or cost.get("recoveryHourlyUsdCents") != 2.7
        or cost.get("catalogSixHourUpperBoundUsdCents") != 147.6
        or cost.get("incrementalExecutionCeilingUsdCents") != 300
        or cost.get("previousConservativeVkeAndDiagnosticCostUsdCents") != 1100
        or cost.get("aggregateCeilingAfterVmExecutionUsdCents") != 1400
        or cost.get("maximumRuntimeHours") != 6
        or cost.get("authenticatedQuoteRequiredBeforeProvision") is not True
        or cost.get("abortIfQuoteExceedsIncrementalCeiling") is not True
        or cost.get("spendAuthorized") is not False
    ):
        findings.append("cost")

    evidence = _mapping(contract.get("evidenceContract"))
    if (
        set(evidence.get("requiredChecks", [])) != EXPECTED_CHECKS
        or set(evidence.get("requiredArtifacts", [])) != EXPECTED_ARTIFACTS
        or evidence.get("timestampsMustBeUtc") is not True
        or evidence.get("artifactSha256Required") is not True
        or evidence.get("rawArtifactsPersistBeforeAggregation") is not True
        or evidence.get("mockEvidenceAccepted") is not False
        or evidence.get("localComposeEvidenceAcceptedAsTarget") is not False
        or evidence.get("providerDocumentationAcceptedAsRuntimeEvidence") is not False
        or evidence.get("vmPassMayClaimVke") is not False
        or evidence.get("externalPassMayClaimProductionDeployment") is not False
    ):
        findings.append("evidence_contract")

    automation = _mapping(contract.get("automation"))
    if (
        automation.get("defaultAction") != "OfflinePreflight"
        or automation.get("mutatingActionsRequireFreshHumanGate") is not True
        or automation.get("mutatingActionsRequireApprovalDigest") is not True
        or automation.get("unsafeBroadDeleteAllowed") is not False
    ):
        findings.append("automation")

    scientific = _mapping(contract.get("scientificBoundary"))
    if (
        scientific.get("frozenR3_325")
        != "E-PASS / X-PASS / S-FAIL / C-NO-CLAIM"
        or scientific.get("rerunAllowed") is not False
        or scientific.get("externalValidationIsScientificEvidence") is not False
        or scientific.get("scientificClaimEstablished") is not False
    ):
        findings.append("scientific_boundary")
    return tuple(sorted(set(findings)))


def validate_iac_sources(root: Path = IAC_ROOT) -> tuple[str, ...]:
    findings: list[str] = []
    required = {
        "versions.tf",
        "variables.tf",
        "main.tf",
        "outputs.tf",
        "cloud-init.yaml.tftpl",
        "routemind-compose.yaml",
        "signoz-casting.yaml",
        "gateway-collector.yaml",
        "backend-ingress-collector.yaml",
        "Dockerfile.business-api",
        "Dockerfile.compute-api",
    }
    missing = sorted(name for name in required if not (root / name).is_file())
    if missing:
        findings.append("iac_missing:" + ",".join(missing))
        return tuple(findings)

    terraform = "\n".join(
        (root / name).read_text(encoding="utf-8")
        for name in ("versions.tf", "variables.tf", "main.tf", "outputs.tf")
    )
    counts = Counter(
        match.group(1)
        for match in re.finditer(r'resource\s+"([a-z0-9_]+)"\s+"', terraform)
    )
    if counts != EXPECTED_TERRAFORM_TYPES:
        findings.append("terraform_resource_inventory")
    for forbidden in (
        "vultr_kubernetes",
        "vultr_block_storage",
        "vultr_load_balancer",
        'subnet = "0.0.0.0"',
        "subnet_size = 0",
    ):
        if forbidden in terraform:
            findings.append("terraform_forbidden:" + forbidden)
    for label, pattern, expected_count in (
        ("primary_plan", r'(?m)^\s*plan\s*=\s*"vc2-8c-32gb"\s*$', 1),
        ("recovery_plan", r'(?m)^\s*plan\s*=\s*"vc2-2c-4gb"\s*$', 1),
        ("vpc_subnet", r'(?m)^\s*v4_subnet\s*=\s*"10\.77\.0\.0"\s*$', 1),
        ("vpc_mask", r"(?m)^\s*v4_subnet_mask\s*=\s*24\s*$", 1),
        ("ssh_port", r'(?m)^\s*port\s*=\s*"22"\s*$', 2),
    ):
        if len(re.findall(pattern, terraform)) != expected_count:
            findings.append("terraform_missing_boundary:" + label)
    for field, value in (
        ("backups", '"disabled"'),
        ("enable_ipv6", "false"),
        ("ddos_protection", "false"),
    ):
        if len(re.findall(rf"(?m)^\s*{field}\s*=\s*{value}\s*$", terraform)) != 2:
            findings.append("terraform_missing_boundary:" + field)

    compose = (root / "routemind-compose.yaml").read_text(encoding="utf-8")
    services = set(
        re.findall(r"(?m)^  ([a-z][a-z0-9-]+):\s*$", compose)
    )
    required_services = {
        "postgres",
        "rabbitmq",
        "redis",
        "business-api",
        "compute-api",
        "routemind-collector",
        "backend-ingress",
        "qualification",
    }
    if not required_services.issubset(services):
        findings.append("compose_services")
    if re.search(r"(?m)^\s+ports:\s*$", compose):
        findings.append("compose_host_ports")
    if compose.count("internal: true") < 2 or "external: true" not in compose:
        findings.append("compose_network_boundaries")
    if (
        "ROUTEMIND_OTLP_EXPORT_ENABLED: \"true\"" not in compose
        or "routemind-logs:/var/log/routemind" not in compose
    ):
        findings.append("compose_telemetry_enablement")
    if "0.0.0.0/0" in compose or "::/0" in compose:
        findings.append("compose_public_cidr")

    casting = (root / "signoz-casting.yaml").read_text(encoding="utf-8")
    for required_text in (
        "flavor: compose",
        "mode: docker",
        "signoz/signoz:v0.139.0",
        "127.0.0.1:8080:8080",
        "/services/ingester/ports",
        "value: []",
    ):
        if required_text not in casting:
            findings.append("signoz_casting:" + required_text)
    if "latest" in casting:
        findings.append("signoz_mutable_tag")

    gateway = (root / "gateway-collector.yaml").read_text(encoding="utf-8")
    backend = (root / "backend-ingress-collector.yaml").read_text(encoding="utf-8")
    if "file_storage" not in gateway or "client_ca_file" not in gateway:
        findings.append("gateway_queue_or_mtls")
    if (
        "filelog/business" not in gateway
        or "filelog/compute" not in gateway
        or "routemind-business-api" not in gateway
        or "routemind-compute-api" not in gateway
    ):
        findings.append("gateway_log_export")
    if "client_ca_file" not in backend or "signoz-ingester:4318" not in backend:
        findings.append("backend_ingress_mtls")
    return tuple(sorted(set(findings)))


def contract_summary(contract: Mapping[str, Any]) -> dict[str, Any]:
    cost = _mapping(contract["cost"])
    return {
        "valid": True,
        "contractId": contract["contractId"],
        "contractDigest": canonical_digest(contract),
        "contractByteSha256": byte_digest(CONTRACT_PATH),
        "status": contract["status"],
        "provider": contract["approvalBoundary"]["provider"],
        "region": contract["approvalBoundary"]["region"],
        "backend": contract["backendDecision"]["selected"],
        "maximumRuntimeHours": cost["maximumRuntimeHours"],
        "incrementalExecutionCeilingUsdCents": cost[
            "incrementalExecutionCeilingUsdCents"
        ],
        "resourceCreationAuthorized": contract["approvalBoundary"][
            "resourceCreationAuthorized"
        ],
        "externalValidationExecuted": contract["scope"]["externalValidationExecuted"],
        "vkeStatus": contract["vkeDiagnosticFreeze"]["status"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate the platform-neutral R4 Vultr Tokyo VM preparation"
    )
    parser.add_argument("--contract", type=Path, default=CONTRACT_PATH)
    parser.add_argument("--skip-iac", action="store_true")
    arguments = parser.parse_args()
    try:
        contract = load_object(arguments.contract)
        deployment = load_object(DEPLOYMENT_CONTRACT_PATH)
        findings = list(validate_contract(contract, deployment))
        if not arguments.skip_iac:
            findings.extend(validate_iac_sources())
    except VmExternalValidationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    if findings:
        for finding in sorted(set(findings)):
            print(f"ERROR: {finding}", file=sys.stderr)
        return 1
    print(json.dumps(contract_summary(contract), sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
