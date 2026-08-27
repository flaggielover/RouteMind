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

from r4_vm_external_validation import validate_iac_sources as validate_runtime_sources

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = (
    ROOT
    / "contracts"
    / "external-validation"
    / "r4-vultr-tokyo-vm-external-validation-v2.json"
)
IAC_ROOT = ROOT / "infra" / "external-validation" / "vultr-tokyo-vm-v2"
RUNTIME_ROOT = ROOT / "infra" / "external-validation" / "vultr-tokyo-vm"
DEPLOYMENT_CONTRACT_PATH = (
    ROOT / "contracts" / "deployment" / "r4-401-vultr-tokyo-v1.json"
)

V1_DIGEST = "2c6bd381ea8bdbf6a2c91864ec4bbf7589d434b19f043375322138ad7bfc608a"
EXPECTED_TASKS = {"R4-405", "R4-406"}
EXPECTED_RECOMPUTE = {"R4-407", "R4-408", "R4-409", "R4-430", "R4-451"}
EXPECTED_PLANS = {
    "primary-validation-vm": "vc2-8c-32gb",
    "recovery-validation-vm": "vc2-2c-4gb",
}
EXPECTED_TERRAFORM_TYPES = Counter(
    {"vultr_firewall_group": 1, "vultr_firewall_rule": 2, "vultr_instance": 2}
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
SHA256 = re.compile(r"^[0-9a-f]{64}$")


class VmExternalValidationV2Error(ValueError):
    pass


def load_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise VmExternalValidationV2Error(f"cannot load JSON object: {path}") from exc
    if not isinstance(value, dict):
        raise VmExternalValidationV2Error(f"JSON root must be an object: {path}")
    return value


def canonical_digest(value: Mapping[str, Any]) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def byte_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _all_false(mapping: Mapping[str, Any], names: tuple[str, ...]) -> bool:
    return all(mapping.get(name) is False for name in names)


def validate_contract(
    contract: Mapping[str, Any], deployment: Mapping[str, Any]
) -> tuple[str, ...]:
    findings: list[str] = []
    if (
        contract.get("schemaVersion") != 1
        or contract.get("contractId") != "r4-vultr-tokyo-vm-external-validation-v2"
        or contract.get("status")
        != "PREPARED_VM_EXTERNAL_EXECUTION_V2_HUMAN_GATE"
    ):
        findings.append("identity")

    predecessor = _mapping(contract.get("predecessor"))
    if (
        predecessor.get("contractId")
        != "r4-vultr-tokyo-vm-external-validation-v1"
        or predecessor.get("canonicalSha256") != V1_DIGEST
        or predecessor.get("executionId") != "r4-vm-20260826t182938z-d3255b7d6c"
        or predecessor.get("digestConsumed") is not True
        or predecessor.get("reusable") is not False
        or predecessor.get("result") != "VPC_QUOTA_BLOCKED_BEFORE_VM_CREATION"
    ):
        findings.append("predecessor")

    scope = _mapping(contract.get("scope"))
    if (
        set(scope.get("qualificationTasks", [])) != EXPECTED_TASKS
        or set(scope.get("recomputeAfterQualification", [])) != EXPECTED_RECOMPUTE
        or not _all_false(
            scope,
            ("productionDeploymentClaimed", "externalValidationExecuted", "paidResourcesCreated"),
        )
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
    ):
        findings.append("vke_freeze")

    quota = _mapping(contract.get("quotaResolution"))
    related = _mapping(quota.get("nrtRelatedResourceCounts"))
    if (
        quota.get("auditMode") != "READ_ONLY"
        or quota.get("providerMutationPerformed") is not False
        or quota.get("nrtVpcCount") != 5
        or set(related) != {
            "instances",
            "kubernetesClusters",
            "loadBalancers",
            "bareMetal",
            "managedDatabases",
        }
        or any(value != 0 for value in related.values())
        or quota.get("existingVpcReuseProvenSafe") is not False
        or quota.get("existingVpcReuseDisposition") != "NOT_SAFE_TO_REUSE"
        or quota.get("unusedInferenceAllowed") is not False
        or quota.get("selectedTopology") != "NO_NEW_VPC"
        or quota.get("vpcCreateCount") != 0
        or quota.get("vpcReuseCount") != 0
    ):
        findings.append("quota_resolution")

    audit = _mapping(contract.get("evidenceContractAudit"))
    classification = _mapping(audit.get("propertyClassification"))
    deferred = audit.get("deferredVke", [])
    deferred_ids = {
        item.get("id")
        for item in deferred
        if isinstance(item, Mapping) and item.get("disposition") == "DEFERRED_VKE"
    }
    semantics = _mapping(audit.get("closureSemantics"))
    if (
        audit.get("conclusion") != "VPC_IS_IMPLEMENTATION_CHOICE_NOT_REQUIRED_PROPERTY"
        or classification.get("newVpc") != "IMPLEMENTATION_CHOICE"
        or any(
            value != "REQUIRED_PROPERTY"
            for key, value in classification.items()
            if key != "newVpc"
        )
        or deferred_ids != EXPECTED_DEFERRED_VKE
        or len(deferred) != len(EXPECTED_DEFERRED_VKE)
        or semantics.get("vmEvidenceMayQualifyPlatformNeutralR4_405AndR4_406Properties")
        is not True
        or not _all_false(
            semantics,
            (
                "vmEvidenceMayClaimVkeValidation",
                "vmEvidenceMayClaimProductionDeployment",
                "deferredVkeItemsMayBeMarkedPassed",
            ),
        )
    ):
        findings.append("property_audit")

    approval = _mapping(contract.get("approvalBoundary"))
    deployment_approval = _mapping(deployment.get("approval"))
    deployment_target = _mapping(deployment.get("target"))
    if (
        approval.get("providerAndResidencyApproved") is not True
        or approval.get("provider") != "Vultr"
        or approval.get("region") != "nrt"
        or approval.get("dataResidency") != "Tokyo, Japan"
        or approval.get("requiredFinalGate")
        != "ROUTEMIND TOKYO VM EXTERNAL VALIDATION V2 HUMAN GATE"
        or approval.get("approvalDigestEnvironmentVariable")
        != "ROUTEMIND_VM_EXTERNAL_EXECUTION_V2_APPROVAL_DIGEST"
        or not _all_false(
            approval,
            ("resourceCreationAuthorized", "spendAuthorized", "liveMutationCallsAuthorized"),
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
        or backend_security.get("directBackendPortsPublished") is not False
        or set(backend_security.get("foundryInvocationRequiredFlags", []))
        != {"--no-ledger", "--no-updater"}
        or any(
            backend_security.get(name) is not True
            for name in (
                "metastoreCredentialGeneratedAtExecution",
                "clickHouseCredentialGeneratedAtExecution",
                "credentialsInjectedFromAclRestrictedSecretFiles",
                "foundryProductTelemetryDisabledOrEgressBlockedBeforeTargetForge",
                "deploymentMustFailIfCredentialOrTelemetryControlCannotBeVerified",
            )
        )
        or any(
            backend_security.get(name) is not False
            for name in (
                "signozAnalyticsEnabled",
                "signozStatsReporterEnabled",
                "signozStatsReporterIdentityCollectionEnabled",
            )
        )
    ):
        findings.append("backend")

    infrastructure = _mapping(contract.get("infrastructure"))
    resources = infrastructure.get("resources", [])
    by_id = {str(item.get("id")): item for item in resources if isinstance(item, Mapping)}
    actual_plans = {key: _mapping(by_id.get(key)).get("plan") for key in EXPECTED_PLANS}
    counts = _mapping(infrastructure.get("terraformResourceCounts"))
    if (
        actual_plans != EXPECTED_PLANS
        or len(resources) != 2
        or any(_mapping(item).get("region") != "nrt" for item in resources)
        or infrastructure.get("vpcMode") != "NONE"
        or infrastructure.get("vpcCreateCount") != 0
        or infrastructure.get("vpcReuseCount") != 0
        or counts != {
            "vultr_firewall_group": 1,
            "vultr_firewall_rule": 2,
            "vultr_instance": 2,
            "vultr_vpc": 0,
        }
        or infrastructure.get("publicLoadBalancers") != 0
        or infrastructure.get("blockStorageVolumes") != 0
        or infrastructure.get("vkeClusters") != 0
        or infrastructure.get("publicApplicationIngress") is not False
        or infrastructure.get("providerAutomaticBackups") is not False
        or infrastructure.get("maximumRuntimeHours") != 6
    ):
        findings.append("infrastructure")

    network = _mapping(contract.get("network"))
    rules = network.get("publicIngressRules", [])
    expected_rules = [
        {
            "id": "operator-ssh",
            "protocol": "tcp",
            "port": 22,
            "source": "ROUTEMIND_OPERATOR_CIDR",
            "subnetSize": 32,
            "purpose": "operator administration",
        },
        {
            "id": "recovery-to-primary-ssh",
            "protocol": "tcp",
            "port": 22,
            "source": "RECOVERY_INSTANCE_MAIN_IP",
            "subnetSize": 32,
            "purpose": "encrypted recovery package pull",
        },
    ]
    zero_port_fields = (
        "publishedApplicationPorts",
        "publishedDatabasePorts",
        "publishedMessagingPorts",
        "publishedCachePorts",
        "publishedOtlpPorts",
        "publishedCollectorHealthPorts",
        "publishedBackendPorts",
    )
    if (
        rules != expected_rules
        or network.get("firewallGroupCount") != 1
        or set(network.get("forbiddenPublicCidrs", [])) != {"0.0.0.0/0", "::/0"}
        or any(network.get(name) != 0 for name in zero_port_fields)
        or not str(network.get("signozUi", "")).startswith("127.0.0.1:8080")
    ):
        findings.append("network")

    inter_vm = _mapping(contract.get("interVmSecurity"))
    if (
        inter_vm.get("transport") != "SSH_22_TCP"
        or inter_vm.get("source") != "RECOVERY_INSTANCE_MAIN_IP/32"
        or inter_vm.get("destinationRole") != "primary-validation"
        or any(
            inter_vm.get(name) is not True
            for name in (
                "sourceRuleCreatedOnlyAfterRecoveryIdentityExists",
                "publicKeyAuthenticationOnly",
                "strictHostKeyCheckingRequired",
                "hostKeyFingerprintPersistedBeforeTransfer",
                "payloadEncryptedBeforeTransfer",
                "payloadSha256Bound",
            )
        )
        or any(
            inter_vm.get(name) is not False
            for name in (
                "passwordAuthenticationAllowed",
                "rawPayloadMayTransitOperatorMachine",
                "plaintextServiceTrafficBetweenVmsAllowed",
            )
        )
    ):
        findings.append("inter_vm_security")

    topology = _mapping(contract.get("telemetryTopology"))
    tls = _mapping(topology.get("tls"))
    if (
        set(topology.get("signals", [])) != EXPECTED_SIGNALS
        or set(topology.get("requiredCorrelationBoundaries", [])) != EXPECTED_BOUNDARIES
        or not str(topology.get("logSource", "")).startswith(
            "read-only shared application log volume"
        )
        or topology.get("gatewayPersistentQueue") is not True
        or topology.get("gatewayPersistentQueueMaximumGiB") != 10
        or any(
            tls.get(name) is not True
            for name in (
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
        or cost.get("maximumRuntimeHours") != 6
        or cost.get("authenticatedQuoteRequiredBeforeProvision") is not True
        or cost.get("abortIfQuoteExceedsIncrementalCeiling") is not True
        or cost.get("spendAuthorized") is not False
    ):
        findings.append("cost")

    evidence = _mapping(contract.get("evidenceContract"))
    if (
        evidence.get("schema") != "r4-vm-external-validation-evidence.v2"
        or "vpc_create_count_zero" not in evidence.get("requiredChecks", [])
        or "encrypted_cross_vm_backup_restore" not in evidence.get("requiredChecks", [])
        or "inter-vm-ssh-identity" not in evidence.get("requiredArtifacts", [])
        or evidence.get("timestampsMustBeUtc") is not True
        or evidence.get("artifactSha256Required") is not True
        or evidence.get("rawArtifactsPersistBeforeAggregation") is not True
        or not _all_false(
            evidence,
            (
                "mockEvidenceAccepted",
                "localComposeEvidenceAcceptedAsTarget",
                "providerDocumentationAcceptedAsRuntimeEvidence",
                "vmPassMayClaimVke",
                "externalPassMayClaimProductionDeployment",
            ),
        )
    ):
        findings.append("evidence_contract")

    automation = _mapping(contract.get("automation"))
    if (
        automation.get("iacRoot") != "infra/external-validation/vultr-tokyo-vm-v2"
        or automation.get("runtimeRoot") != "infra/external-validation/vultr-tokyo-vm"
        or automation.get("planValidator") != "scripts/r4_vm_external_plan_v2.py"
        or automation.get("defaultAction") != "OfflinePreflight"
        or automation.get("mutatingActionsRequireFreshHumanGate") is not True
        or automation.get("mutatingActionsRequireApprovalDigest") is not True
        or automation.get("exactCreatePlanRequiredBeforeApply") is not True
        or automation.get("applyMayUseOnlyValidatedSavedPlan") is not True
        or set(automation.get("ownedProviderResourceTypes", []))
        != {"vultr_instance", "vultr_firewall_group", "vultr_firewall_rule"}
        or automation.get("vpcDeleteAllowed") is not False
        or automation.get("unsafeBroadDeleteAllowed") is not False
        or "no VPC is owned or deleted" not in str(automation.get("teardown", ""))
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
    required = {"versions.tf", "variables.tf", "main.tf", "outputs.tf", "cloud-init.yaml.tftpl"}
    missing = sorted(name for name in required if not (root / name).is_file())
    if missing:
        return ("iac_missing:" + ",".join(missing),)

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
        "vultr_vpc",
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
        ("ssh_port", r'(?m)^\s*port\s*=\s*"22"\s*$', 2),
        ("operator_source", r"(?m)^\s*subnet\s*=\s*local\.operator_ipv4\s*$", 1),
        (
            "recovery_source",
            r"(?m)^\s*subnet\s*=\s*vultr_instance\.recovery\.main_ip\s*$",
            1,
        ),
        ("exact_32", r"(?m)^\s*subnet_size\s*=\s*32\s*$", 2),
        ("vpc_create_count", r"(?m)^\s*vpc_create_count\s*=\s*0\s*$", 1),
        ("empty_vpc_ids", r"(?m)^\s*vpc_ids\s*=\s*\[\]\s*$", 2),
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
    if terraform.count("firewall_group_id = vultr_firewall_group.validation.id") != 4:
        findings.append("terraform_firewall_ownership")
    if len(re.findall(r"(?m)^\s*vpc_ids\s*=", terraform)) != 2:
        findings.append("terraform_vpc_attachment")
    cloud_init = (root / "cloud-init.yaml.tftpl").read_text(encoding="utf-8")
    if len(re.findall(r"(?m)^ssh_pwauth:\s*false\s*$", cloud_init)) != 1:
        findings.append("cloud_init_password_auth")
    return tuple(sorted(set(findings)))


def contract_summary(contract: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "valid": True,
        "contractId": contract["contractId"],
        "contractDigest": canonical_digest(contract),
        "contractByteSha256": byte_digest(CONTRACT_PATH),
        "status": contract["status"],
        "provider": contract["approvalBoundary"]["provider"],
        "region": contract["approvalBoundary"]["region"],
        "vpcMode": contract["infrastructure"]["vpcMode"],
        "vpcCreateCount": contract["infrastructure"]["vpcCreateCount"],
        "maximumRuntimeHours": contract["cost"]["maximumRuntimeHours"],
        "incrementalExecutionCeilingUsdCents": contract["cost"][
            "incrementalExecutionCeilingUsdCents"
        ],
        "resourceCreationAuthorized": contract["approvalBoundary"][
            "resourceCreationAuthorized"
        ],
        "externalValidationExecuted": contract["scope"]["externalValidationExecuted"],
        "vkeStatus": contract["vkeDiagnosticFreeze"]["status"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the no-new-VPC Tokyo VM v2 contract")
    parser.add_argument("--contract", type=Path, default=CONTRACT_PATH)
    parser.add_argument("--skip-iac", action="store_true")
    arguments = parser.parse_args()
    try:
        contract = load_object(arguments.contract)
        deployment = load_object(DEPLOYMENT_CONTRACT_PATH)
        findings = list(validate_contract(contract, deployment))
        if not arguments.skip_iac:
            findings.extend(validate_iac_sources())
            findings.extend("runtime:" + item for item in validate_runtime_sources(RUNTIME_ROOT))
    except VmExternalValidationV2Error as exc:
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
