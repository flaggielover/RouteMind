from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = (
    ROOT
    / "contracts"
    / "external-validation"
    / "r4-vultr-tokyo-external-validation-v1.json"
)
DEPLOYMENT_CONTRACT_PATH = (
    ROOT / "contracts" / "deployment" / "r4-401-vultr-tokyo-v1.json"
)

EXPECTED_TASKS = {"R4-405", "R4-406"}
EXPECTED_INDEPENDENT_GATES = {"R4-410", "R4-422"}
EXPECTED_BOUNDARIES = {"http", "messaging", "worker", "simulation", "experiment"}
EXPECTED_RESOURCE_TYPES = {
    "Vultr Kubernetes Engine",
    "Vultr Cloud Compute",
    "Vultr Block Storage",
}
EXPECTED_TERRAFORM_TYPES = {
    "vultr_firewall_group": 1,
    "vultr_firewall_rule": 2,
    "vultr_instance": 1,
    "vultr_kubernetes": 1,
}
EXPECTED_ARTIFACTS = {
    "authenticated-resource-manifest",
    "environment-version-manifest",
    "collector-health",
    "actual-routemind-workload",
    "trace-query",
    "metric-query",
    "correlated-log-query",
    "leakage-scan",
    "failure-recovery-timeline",
    "target-recovery-report",
    "resource-usage",
    "cost-bound",
    "cleanup-inventory",
}
SHA256 = re.compile(r"^[0-9a-f]{64}$")
TRACE_ID = re.compile(r"^[0-9a-f]{32}$")
EXECUTION_ID = re.compile(r"^r4-ext-[0-9]{8}t[0-9]{6}z-[0-9a-f]{7,12}$")


class ExternalValidationError(ValueError):
    pass


def load_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ExternalValidationError(f"cannot load JSON object: {path}") from exc
    if not isinstance(value, dict):
        raise ExternalValidationError(f"JSON root must be an object: {path}")
    return value


def canonical_digest(value: Mapping[str, Any], *, omit: str | None = None) -> str:
    payload = dict(value)
    if omit is not None:
        payload.pop(omit, None)
    canonical = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _sha256(value: object) -> bool:
    return isinstance(value, str) and SHA256.fullmatch(value) is not None


def _utc_timestamp(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.endswith("Z"):
        return None
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        return None
    return parsed.astimezone(UTC)


def validate_contract(
    contract: Mapping[str, Any], deployment: Mapping[str, Any]
) -> tuple[str, ...]:
    findings: list[str] = []
    if (
        contract.get("schemaVersion") != 1
        or contract.get("contractId")
        != "r4-vultr-tokyo-external-validation-v1"
        or contract.get("status") != "PREPARED_EXTERNAL_EXECUTION_HUMAN_GATE"
    ):
        findings.append("identity")

    scope = contract.get("scope", {})
    if (
        set(scope.get("qualificationTasks", [])) != EXPECTED_TASKS
        or set(scope.get("auditedIndependentHumanGates", []))
        != EXPECTED_INDEPENDENT_GATES
        or scope.get("productionDeploymentClaimed") is not False
        or scope.get("externalValidationExecuted") is not False
    ):
        findings.append("scope")

    approval = contract.get("approvalBoundary", {})
    if (
        approval.get("providerAndResidencyApproved") is not True
        or approval.get("provider") != "Vultr"
        or approval.get("region") != "nrt"
        or approval.get("dataResidency") != "Tokyo, Japan"
        or approval.get("requiredFinalGate") != "EXTERNAL EXECUTION HUMAN GATE"
        or approval.get("approvalDigestEnvironmentVariable")
        != "ROUTEMIND_EXTERNAL_EXECUTION_APPROVAL_DIGEST"
        or any(
            approval.get(field) is not False
            for field in (
                "resourceCreationAuthorized",
                "spendAuthorized",
                "liveMutationCallsAuthorized",
            )
        )
    ):
        findings.append("approval_boundary")

    deployment_approval = deployment.get("approval", {})
    deployment_target = deployment.get("target", {})
    if (
        deployment_approval.get("provider") != approval.get("provider")
        or deployment_target.get("regionId") != approval.get("region")
        or deployment_approval.get("dataResidency") != approval.get("dataResidency")
        or deployment_approval.get("resourceCreationAuthorized") is not False
        or deployment_approval.get("spendAuthorized") is not False
        or deployment_target.get("productionVerified") is not False
    ):
        findings.append("r4_401_alignment")

    backend = contract.get("backendDecision", {})
    candidates = backend.get("candidates", [])
    dispositions = {
        candidate.get("id"): candidate.get("disposition")
        for candidate in candidates
        if isinstance(candidate, Mapping)
    }
    pinned = backend.get("pinnedArtifacts", {})
    if (
        backend.get("selected") != "self-hosted-signoz"
        or backend.get("selectionStatus")
        != "APPROVED_FOR_BOUNDED_EXTERNAL_VALIDATION_NOT_DEPLOYED"
        or dispositions.get("self-hosted-signoz") != "SELECTED"
        or set(dispositions) != {
            "self-hosted-signoz",
            "grafana-otel-lgtm",
            "self-hosted-uptrace",
        }
        or pinned.get("signozHelmChartVersion") != "0.138.0"
        or not _sha256(pinned.get("signozHelmChartSha256"))
        or pinned.get("otelCollectorContribVersion") != "0.159.0"
        or pinned.get("artifactDigestResolutionRequiredBeforeDeploy") is not True
    ):
        findings.append("backend_decision")

    infrastructure = contract.get("infrastructure", {})
    resources = infrastructure.get("resources", [])
    resource_types = {
        item.get("type") for item in resources if isinstance(item, Mapping)
    }
    vke = next(
        (
            item
            for item in resources
            if isinstance(item, Mapping) and item.get("id") == "validation-vke"
        ),
        {},
    )
    recovery = next(
        (
            item
            for item in resources
            if isinstance(item, Mapping)
            and item.get("id") == "recovery-drill-host"
        ),
        {},
    )
    if (
        resource_types != EXPECTED_RESOURCE_TYPES
        or vke.get("region") != "nrt"
        or vke.get("workerPlan") != "vhp-4c-8gb-amd"
        or vke.get("workerCount") != 3
        or vke.get("haControlPlane") is not True
        or vke.get("controlPlaneFirewall")
        != {
            "enabled": True,
            "port": 6443,
            "source": "ROUTEMIND_OPERATOR_CIDR",
            "subnetSizeRequired": 32,
        }
        or recovery.get("region") != "nrt"
        or recovery.get("plan") != "vhp-2c-4gb-amd"
        or recovery.get("automaticBackups") is not False
        or infrastructure.get("resourceLimits", {}).get("observabilityNamespaceStorage") != "60Gi"
        or infrastructure.get("resourceLimits", {}).get("persistentVolumeClaimCountMaximum") != 5
        or infrastructure.get("publicLoadBalancers") != 0
        or infrastructure.get("publicApplicationIngress") is not False
        or infrastructure.get("maximumRuntimeHours") != 8
    ):
        findings.append("infrastructure")

    topology = contract.get("telemetryTopology", {})
    boundaries = topology.get("networkBoundaries", [])
    boundary_ids = {
        item.get("id") for item in boundaries if isinstance(item, Mapping)
    }
    boundary_by_id = {
        item.get("id"): item for item in boundaries if isinstance(item, Mapping)
    }
    tls = topology.get("tls", {})
    if (
        topology.get("collectorMode")
        != "TWO_REPLICA_GATEWAY_WITH_BOUNDED_PERSISTENT_QUEUE"
        or topology.get("backendMode")
        != "SINGLE_VALIDATION_BACKEND_NOT_PRODUCTION_HA"
        or boundary_ids
        != {
            "application-to-routemind-collector",
            "routemind-collector-to-signoz",
            "collector-health-and-metrics",
            "signoz-ui",
            "recovery-operator",
            "provider-api",
            "provider-kubernetes-control-plane",
        }
        or boundary_by_id.get("provider-api", {}).get("port") != 443
        or boundary_by_id.get("provider-kubernetes-control-plane", {}).get("port")
        != 6443
        or boundary_by_id.get("provider-api", {}).get("exposure")
        != "Vultr_API_outbound_only"
        or boundary_by_id.get("provider-kubernetes-control-plane", {}).get(
            "exposure"
        )
        != "temporary_public_control_plane_operator_cidr_only"
        or tls.get("publicPlaintextAllowed") is not False
        or tls.get("otlpMutualTlsRequired") is not True
        or tls.get("privateKeysPersistedAfterCleanup") is not False
    ):
        findings.append("telemetry_topology")

    secrets = contract.get("secretHandling", {})
    if (
        set(secrets.get("userConfiguredSecretNames", []))
        != {"VULTR_API_KEY", "ROUTEMIND_SSH_PRIVATE_KEY_PATH"}
        or set(secrets.get("userConfiguredNonSecretNames", []))
        != {"ROUTEMIND_VULTR_SSH_KEY_ID", "ROUTEMIND_OPERATOR_CIDR"}
        or secrets.get("secretValueLoggingAllowed") is not False
        or not {
            "Git",
            "evidence",
            "logs",
            "fixtures",
            "screenshots",
            "Progress Capsule",
            "tracked .env files",
        }.issubset(set(secrets.get("forbiddenLocations", [])))
    ):
        findings.append("secret_handling")

    governance = contract.get("dataGovernance", {})
    if (
        governance.get("allowedWorkloadData") != "SYNTHETIC_NO_CUSTOMER_DATA"
        or governance.get("payloadResidency") != "Vultr nrt only"
        or governance.get("backendRawRetentionMaximumHours") != 8
        or governance.get("cleanupDeletesBackendStorage") is not True
        or governance.get("providerAutomaticBackups") is not False
    ):
        findings.append("data_governance")

    cost = contract.get("cost", {})
    if (
        cost.get("currency") != "USD"
        or cost.get("publicCatalogExpectedMaximumUsdCents") != 500
        or cost.get("executionAuthorizationCeilingUsdCents") != 1500
        or cost.get("emergencyMonthlyCeilingUsdCents") != 30000
        or cost.get("maximumRuntimeHours") != 8
        or cost.get("authenticatedQuoteRequiredBeforeProvision") is not True
        or cost.get("abortIfQuoteExceedsExecutionCeiling") is not True
        or cost.get("spendAuthorized") is not False
    ):
        findings.append("cost_boundary")

    automation = contract.get("automation", {})
    if (
        automation.get("defaultAction") != "OfflinePreflight"
        or automation.get("mutatingActionsRequireExplicitSwitch") is not True
        or automation.get("mutatingActionsRequireApprovalDigest") is not True
        or set(automation.get("provisionPlanAllowedResourceTypes", []))
        != set(EXPECTED_TERRAFORM_TYPES)
        or automation.get("provisionPlanExactResourceCounts")
        != EXPECTED_TERRAFORM_TYPES
        or automation.get("unsafeBroadDeleteAllowed") is not False
    ):
        findings.append("automation_boundary")

    evidence = contract.get("evidenceContract", {})
    if (
        evidence.get("schema") != "r4-external-validation-evidence.v1"
        or set(evidence.get("requiredCorrelationBoundaries", []))
        != EXPECTED_BOUNDARIES
        or set(evidence.get("requiredArtifacts", [])) != EXPECTED_ARTIFACTS
        or len(set(evidence.get("requiredChecks", []))) != 17
        or evidence.get("artifactSha256Required") is not True
        or evidence.get("mockEvidenceAccepted") is not False
        or evidence.get("composeEvidenceAcceptedAsTarget") is not False
        or evidence.get("providerDocumentationAcceptedAsRuntimeEvidence") is not False
        or evidence.get("externalPassMayClaimProductionDeployment") is not False
    ):
        findings.append("evidence_contract")

    science = contract.get("scientificBoundary", {})
    if science != {
        "frozenR3_325": "E-PASS / X-PASS / S-FAIL / C-NO-CLAIM",
        "rerunAllowed": False,
        "externalValidationIsScientificEvidence": False,
        "scientificClaimEstablished": False,
    }:
        findings.append("scientific_boundary")
    return tuple(sorted(set(findings)))


def validate_evidence(
    report: Mapping[str, Any], contract: Mapping[str, Any]
) -> tuple[str, ...]:
    findings: list[str] = []
    contract_digest = canonical_digest(contract)
    if (
        report.get("schemaVersion") != "r4-external-validation-evidence.v1"
        or report.get("contractDigest") != contract_digest
        or report.get("classification") != "EXTERNAL_VALIDATION_PASS"
        or report.get("productionDeploymentVerified") is not False
    ):
        findings.append("identity")

    execution = report.get("execution", {})
    started = _utc_timestamp(execution.get("startedAt"))
    completed = _utc_timestamp(execution.get("completedAt"))
    if (
        not isinstance(execution, Mapping)
        or not isinstance(execution.get("id"), str)
        or EXECUTION_ID.fullmatch(str(execution.get("id"))) is None
        or started is None
        or completed is None
        or completed <= started
        or (completed - started).total_seconds() > 8 * 3600
        or execution.get("credentialedProviderCalls") is not True
        or execution.get("mockEvidence") is not False
        or execution.get("composeEvidencePromoted") is not False
        or execution.get("workloadDataClass") != "SYNTHETIC_NO_CUSTOMER_DATA"
    ):
        findings.append("execution")

    target = report.get("target", {})
    if (
        target.get("provider") != "Vultr"
        or target.get("region") != "nrt"
        or target.get("city") != "Tokyo"
        or target.get("country") != "JP"
        or target.get("dataResidency") != "Tokyo, Japan"
        or target.get("identitySource") != "authenticated_vultr_api"
    ):
        findings.append("target_identity")

    resources = report.get("resources", [])
    if not isinstance(resources, list) or not resources:
        findings.append("resources")
        resources = []
    resource_types = {
        item.get("type") for item in resources if isinstance(item, Mapping)
    }
    for item in resources:
        if (
            not isinstance(item, Mapping)
            or not item.get("providerId")
            or item.get("region") != "nrt"
            or _utc_timestamp(item.get("createdAt")) is None
            or _utc_timestamp(item.get("deletedAt")) is None
            or item.get("cleanupVerified") is not True
        ):
            findings.append("resource_identity_or_cleanup")
            break
    if resource_types != EXPECTED_RESOURCE_TYPES:
        findings.append("resource_types")

    required_checks = set(contract["evidenceContract"]["requiredChecks"])
    checks = report.get("checks", {})
    if not isinstance(checks, Mapping) or set(checks) != required_checks:
        findings.append("check_set")
        checks = {}
    for check in checks.values():
        if (
            not isinstance(check, Mapping)
            or check.get("status") != "PASS"
            or _utc_timestamp(check.get("observedAt")) is None
            or not check.get("artifactIds")
        ):
            findings.append("check_failure")
            break

    correlation = report.get("correlation", {})
    trace_id = correlation.get("traceId")
    if (
        not isinstance(trace_id, str)
        or TRACE_ID.fullmatch(trace_id) is None
        or set(correlation.get("boundaries", [])) != EXPECTED_BOUNDARIES
        or correlation.get("singleTrace") is not False
        or correlation.get("actualRouteMindWorkload") is not True
        or correlation.get("syntheticQualificationTraffic") is not True
    ):
        findings.append("correlation")

    tenant = report.get("tenantBoundary", {})
    leakage = report.get("leakage", {})
    if (
        tenant.get("rawIdentifierFindings") != 0
        or tenant.get("pseudonymizedKeysOnly") is not True
        or not isinstance(tenant.get("maximumObservedActiveKeys"), int)
        or not 1 <= tenant.get("maximumObservedActiveKeys", 0) <= 64
        or leakage.get("secretFindings") != 0
        or leakage.get("rawTenantIdentifierFindings") != 0
        or leakage.get("productionDataFindings") != 0
        or leakage.get("scanCompleted") is not True
    ):
        findings.append("tenant_or_leakage")

    usage = report.get("resourceUsage", {})
    if (
        not isinstance(usage.get("peakCpuCores"), (int, float))
        or isinstance(usage.get("peakCpuCores"), bool)
        or not 0 < usage.get("peakCpuCores", 0) <= 12
        or not isinstance(usage.get("peakMemoryMiB"), (int, float))
        or isinstance(usage.get("peakMemoryMiB"), bool)
        or not 0 < usage.get("peakMemoryMiB", 0) <= 24576
        or not isinstance(usage.get("peakStorageGiB"), (int, float))
        or isinstance(usage.get("peakStorageGiB"), bool)
        or not 0 < usage.get("peakStorageGiB", 0) <= 60
    ):
        findings.append("resource_usage")

    cost = report.get("cost", {})
    if (
        cost.get("currency") != "USD"
        or cost.get("source") != "authenticated_vultr_quote_and_runtime_bound"
        or not isinstance(cost.get("upperBoundUsdCents"), int)
        or not 0 < cost.get("upperBoundUsdCents", 0) <= 1500
        or cost.get("withinApprovedCeiling") is not True
    ):
        findings.append("cost")

    artifacts = report.get("artifacts", [])
    artifact_ids = {
        item.get("id") for item in artifacts if isinstance(item, Mapping)
    }
    if artifact_ids != EXPECTED_ARTIFACTS:
        findings.append("artifact_set")
    for artifact in artifacts:
        if (
            not isinstance(artifact, Mapping)
            or not isinstance(artifact.get("path"), str)
            or Path(str(artifact.get("path"))).is_absolute()
            or ".." in Path(str(artifact.get("path"))).parts
            or not _sha256(artifact.get("sha256"))
            or not isinstance(artifact.get("byteSize"), int)
            or artifact.get("byteSize", 0) <= 0
            or _utc_timestamp(artifact.get("capturedAt")) is None
            or artifact.get("containsSecrets") is not False
        ):
            findings.append("artifact_integrity")
            break
    referenced_artifacts = {
        artifact_id
        for check in checks.values()
        if isinstance(check, Mapping)
        for artifact_id in check.get("artifactIds", [])
    }
    if not referenced_artifacts.issubset(artifact_ids):
        findings.append("artifact_reference")

    cleanup = report.get("cleanup", {})
    if (
        cleanup.get("complete") is not True
        or cleanup.get("credentialedInventoryCheck") is not True
        or cleanup.get("remainingResourceIds") != []
        or cleanup.get("localPrivateKeysDeleted") is not True
        or cleanup.get("kubeconfigDeleted") is not True
        or _utc_timestamp(cleanup.get("verifiedAt")) is None
    ):
        findings.append("cleanup")

    qualification = report.get("taskQualification", {})
    if qualification != {
        "R4-405": "TARGET_QUALIFIED",
        "R4-406": "TARGET_DRILL_PASS",
    }:
        findings.append("task_qualification")

    science = report.get("scientificBoundary", {})
    if science != {
        "frozenR3_325": "E-PASS / X-PASS / S-FAIL / C-NO-CLAIM",
        "rerunOccurred": False,
        "externalValidationIsScientificEvidence": False,
        "scientificClaimEstablished": False,
    }:
        findings.append("scientific_boundary")

    if (
        not _sha256(report.get("reportDigest"))
        or report.get("reportDigest") != canonical_digest(report, omit="reportDigest")
    ):
        findings.append("report_digest")
    return tuple(sorted(set(findings)))


def validate_terraform_plan(
    plan: Mapping[str, Any], *, destroy: bool = False, allow_partial_destroy: bool = False
) -> tuple[str, ...]:
    findings: list[str] = []
    changes = plan.get("resource_changes", [])
    if not isinstance(changes, list):
        return ("resource_changes",)
    expected_action = ["delete"] if destroy else ["create"]
    actual_types: Counter[str] = Counter()
    for change in changes:
        if not isinstance(change, Mapping):
            findings.append("resource_change")
            continue
        resource_type = change.get("type")
        actions = change.get("change", {}).get("actions", [])
        if resource_type not in EXPECTED_TERRAFORM_TYPES:
            findings.append(f"resource_type:{resource_type}")
        else:
            actual_types[str(resource_type)] += 1
        if actions != expected_action:
            findings.append(f"resource_action:{change.get('address')}")
    if destroy and allow_partial_destroy:
        if any(
            count > EXPECTED_TERRAFORM_TYPES.get(resource_type, 0)
            for resource_type, count in actual_types.items()
        ):
            findings.append("resource_inventory")
    elif actual_types != Counter(EXPECTED_TERRAFORM_TYPES):
        findings.append("resource_inventory")
    return tuple(sorted(set(findings)))


def contract_summary(contract: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "valid": True,
        "contractId": contract["contractId"],
        "contractDigest": canonical_digest(contract),
        "status": contract["status"],
        "backend": contract["backendDecision"]["selected"],
        "provider": contract["approvalBoundary"]["provider"],
        "region": contract["approvalBoundary"]["region"],
        "maximumRuntimeHours": contract["cost"]["maximumRuntimeHours"],
        "executionAuthorizationCeilingUsdCents": contract["cost"][
            "executionAuthorizationCeilingUsdCents"
        ],
        "resourceCreationAuthorized": contract["approvalBoundary"][
            "resourceCreationAuthorized"
        ],
        "externalValidationExecuted": contract["scope"][
            "externalValidationExecuted"
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate the R4 Vultr Tokyo external-validation preparation"
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--evidence", type=Path)
    group.add_argument("--terraform-plan", type=Path)
    group.add_argument("--finalize-evidence-draft", type=Path)
    parser.add_argument("--destroy-plan", action="store_true")
    parser.add_argument("--allow-partial-destroy", action="store_true")
    arguments = parser.parse_args()

    try:
        contract = load_object(CONTRACT_PATH)
        deployment = load_object(DEPLOYMENT_CONTRACT_PATH)
        findings = list(validate_contract(contract, deployment))
        if arguments.evidence:
            findings.extend(validate_evidence(load_object(arguments.evidence), contract))
        if arguments.terraform_plan:
            findings.extend(
                validate_terraform_plan(
                    load_object(arguments.terraform_plan),
                    destroy=arguments.destroy_plan,
                    allow_partial_destroy=arguments.allow_partial_destroy,
                )
            )
        if arguments.finalize_evidence_draft:
            draft = load_object(arguments.finalize_evidence_draft)
            draft["reportDigest"] = canonical_digest(draft, omit="reportDigest")
            evidence_findings = validate_evidence(draft, contract)
            if evidence_findings:
                findings.extend(evidence_findings)
            else:
                arguments.finalize_evidence_draft.write_text(
                    json.dumps(draft, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
    except ExternalValidationError as exc:
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
