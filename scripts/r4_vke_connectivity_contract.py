from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = (
    ROOT
    / "contracts"
    / "external-validation"
    / "r4-vultr-tokyo-vke-connectivity-diagnostic-v3.json"
)
V2_CONTRACT_DIGEST = "1f78b9d3562a6bac3cfa7b9ad070545e5b1eb2c7c9d88090acc9e765c20dc782"
V1_CONTRACT_DIGEST = "30c9580eb2fe43de1306b299a73c4a1c5d0f286ac7bef4be0c3d0f4b7994a426"


class ConnectivityContractError(ValueError):
    pass


def load_contract(path: Path = CONTRACT_PATH) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConnectivityContractError(f"cannot load contract: {path}") from exc
    if not isinstance(value, dict):
        raise ConnectivityContractError("contract root must be an object")
    return value


def canonical_digest(contract: Mapping[str, Any]) -> str:
    payload = json.dumps(contract, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def validate(contract: Mapping[str, Any]) -> tuple[str, ...]:
    findings: list[str] = []
    if (
        contract.get("schemaVersion") != 1
        or contract.get("contractId") != "r4-vultr-tokyo-vke-connectivity-diagnostic-v3"
        or contract.get("status") != "PREPARED_VKE_CONNECTIVITY_DIAGNOSTIC_V3_HUMAN_GATE"
        or contract.get("supersedesContractDigest") != V2_CONTRACT_DIGEST
    ):
        findings.append("identity")

    scope = contract.get("scope", {})
    if (
        set(scope.get("qualificationTasks", [])) != {"R4-405", "R4-406"}
        or scope.get("productionDeploymentClaimed") is not False
        or scope.get("telemetryPersistence") is not False
        or scope.get("scientificValidation") is not False
        or scope.get("routeMindDeployment") is not False
    ):
        findings.append("scope")

    approval = contract.get("approvalBoundary", {})
    if (
        approval.get("provider") != "Vultr"
        or approval.get("region") != "nrt"
        or approval.get("dataResidency") != "Tokyo, Japan"
        or approval.get("requiredFinalGate") != "VKE CONNECTIVITY DIAGNOSTIC V3 HUMAN GATE"
        or approval.get("resourceCreationAuthorized") is not False
        or approval.get("spendAuthorized") is not False
        or approval.get("liveMutationCallsAuthorized") is not False
    ):
        findings.append("approval")

    infrastructure = contract.get("infrastructure", {})
    resources = infrastructure.get("resources", [])
    resource_ids = {item.get("id") for item in resources if isinstance(item, Mapping)}
    if resource_ids != {"diagnostic-vke", "diagnostic-recovery-host", "diagnostic-recovery-firewall"}:
        findings.append("resources")
    vke = next((item for item in resources if isinstance(item, Mapping) and item.get("id") == "diagnostic-vke"), {})
    recovery = next((item for item in resources if isinstance(item, Mapping) and item.get("id") == "diagnostic-recovery-host"), {})
    if (
        vke.get("type") != "Vultr Kubernetes Engine"
        or vke.get("region") != "nrt"
        or vke.get("workerPlan") != "vhp-4c-8gb-amd"
        or vke.get("workerCount") != 1
        or vke.get("haControlPlane") is not True
        or vke.get("persistentStorageGiB") != 0
        or vke.get("publicLoadBalancers") != 0
        or recovery.get("type") != "Vultr Cloud Compute"
        or recovery.get("region") != "nrt"
        or recovery.get("plan") != "vhp-2c-4gb-amd"
        or recovery.get("automaticBackups") is not False
        or infrastructure.get("maximumRuntimeHours") != 2
        or infrastructure.get("maximumResourceCount") != 6
        or infrastructure.get("noPersistentVolumes") is not True
        or infrastructure.get("noPublicIngress") is not True
    ):
        findings.append("infrastructure_boundary")

    rules = infrastructure.get("firewallRules", [])
    rule_ids = {item.get("id") for item in rules if isinstance(item, Mapping)}
    if rule_ids != {
        "diagnostic-recovery-ssh",
        "diagnostic-vke-api-operator",
        "diagnostic-vke-api-recovery",
    }:
        findings.append("firewall_rules")
    for rule in rules:
        if (
            not isinstance(rule, Mapping)
            or rule.get("protocol") != "tcp"
            or rule.get("subnetSize") != 32
            or rule.get("ipType") != "v4"
            or rule.get("port") not in {22, 6443}
        ):
            findings.append("firewall_rule_shape")
            break
    if (
        any(rule.get("source") == "0.0.0.0/0" for rule in rules if isinstance(rule, Mapping))
        or any(rule.get("source") == "::/0" for rule in rules if isinstance(rule, Mapping))
    ):
        findings.append("firewall_broad_source")

    endpoint = contract.get("endpointContract", {})
    if (
        endpoint.get("scheme") != "https"
        or endpoint.get("port") != 6443
        or endpoint.get("sniRequired") is not True
        or endpoint.get("tlsServerNameMustEqualProviderHostname") is not True
        or endpoint.get("fakeDnsNetwork") != "198.18.0.0/15"
    ):
        findings.append("endpoint")

    ladder = contract.get("readinessLadder", [])
    if ladder != [
        "provider_cluster_state_active",
        "endpoint_hostname_and_provider_ip_present",
        "dns_resolution_recorded",
        "tcp_6443_from_each_observer",
        "tls_client_hello_and_handshake_with_hostname_sni",
        "http_version_response_without_mutation",
    ]:
        findings.append("readiness_ladder")
    backoff = contract.get("backoff", {})
    if (
        backoff.get("initialSeconds") != 2
        or backoff.get("multiplier") != 2
        or backoff.get("maximumSeconds") != 32
        or backoff.get("deadlineMinutes") != 20
        or backoff.get("fixedSleepAloneIsNotEvidence") is not True
    ):
        findings.append("backoff")

    repair = contract.get("repairControls", {})
    if (
        repair.get("oldDigestAccepted") is not False
        or repair.get("resourceShapeChangedFromV1") is not False
        or "identity file" not in repair.get("observerReadiness", "")
        or "bounded retry" not in repair.get("teardownConvergence", "")
        or "independent" not in repair.get("observerFailureIsolation", "")
        or "raw output" not in repair.get("probeEvidenceRetention", "")
    ):
        findings.append("repair_controls")

    prior = contract.get("priorExecution", {})
    if (
        prior.get("classification") != "DIAGNOSTIC_INCOMPLETE"
        or prior.get("rootCauseConfidence") != "INSUFFICIENT_EVIDENCE"
        or prior.get("tokyoObserverResult") != "NOT_RECORDED"
        or "duplicate proxy keys" not in prior.get("directEngineeringCause", "")
        or prior.get("historicalEvidenceImmutable") is not True
        or prior.get("digestConsumedAndNotReusable") is not True
    ):
        findings.append("prior_execution")

    outputs = contract.get("diagnosticOutputs", {})
    if (
        outputs.get("secretValuesPrinted") is not False
        or outputs.get("proxyValuesPrinted") is not False
        or outputs.get("certificateContentsPrinted") is not False
        or "TLS_EOF" not in outputs.get("phaseLabels", [])
        or "TLS_CERT_FAILURE" not in outputs.get("phaseLabels", [])
        or outputs.get("rawPersistedBeforeParse") is not True
        or outputs.get("aggregationFailurePreservesArtifacts") is not True
        or outputs.get("canonicalSchemaVersion") != 2
    ):
        findings.append("diagnostic_output")

    schema = contract.get("probeSchema", {})
    if (
        schema.get("schemaVersion") != 2
        or schema.get("caseSensitiveKeys") is not True
        or schema.get("unknownKeysRejected") is not True
        or schema.get("rawArtifactPersistedBeforeParse") is not True
        or schema.get("phases") != ["dns", "tcp", "tls_client_hello", "tls_handshake", "http"]
        or set(schema.get("observerValues", [])) != {"operator", "tokyo-recovery"}
        or set(schema.get("artifactStatuses", [])) != {"COMPLETE", "EXECUTION_FAILED", "MALFORMED", "MISSING"}
        or len(schema.get("requiredTopLevelKeys", [])) != 13
    ):
        findings.append("probe_schema")

    isolation = contract.get("observerIsolation", {})
    if (
        isolation.get("executionIndependent") is not True
        or isolation.get("parsingIndependent") is not True
        or isolation.get("persistenceIndependent") is not True
        or isolation.get("aggregationAfterBothArtifacts") is not True
        or isolation.get("oneSideFailureCannotPreventOther") is not True
        or isolation.get("missingSideClassification") != "DIAGNOSTIC_INCOMPLETE"
    ):
        findings.append("observer_isolation")

    if contract.get("failureInjection") != [
        "operator_artifact_malformed",
        "observer_artifact_malformed",
        "operator_execution_fails",
        "observer_execution_fails",
        "aggregation_fails",
        "one_side_missing",
    ]:
        findings.append("failure_injection")

    secrets = contract.get("secretHandling", {})
    if (
        set(secrets.get("requiredSecretNames", [])) != {"VULTR_API_KEY", "ROUTEMIND_SSH_PRIVATE_KEY_PATH"}
        or secrets.get("secretValueLoggingAllowed") is not False
        or not {"Git", "evidence", "logs", "fixtures", "screenshots", "tracked .env files"}.issubset(
            set(secrets.get("forbiddenLocations", []))
        )
    ):
        findings.append("secret_handling")

    evidence = contract.get("evidenceContract", {})
    if (
        len(evidence.get("requiredArtifacts", [])) != 13
        or len(evidence.get("requiredChecks", [])) != 13
        or evidence.get("timestampsMustBeUtc") is not True
        or evidence.get("artifactSha256Required") is not True
        or evidence.get("mockEvidenceAccepted") is not False
        or evidence.get("diagnosticDoesNotQualifyR4Tasks") is not True
    ):
        findings.append("evidence_contract")

    cost = contract.get("cost", {})
    if (
        cost.get("currency") != "USD"
        or cost.get("maximumRuntimeHours") != 2
        or cost.get("incrementalExecutionCeilingUsdCents") != 500
        or cost.get("aggregatePriorAttemptsUpperBoundUsdCents") != 880
        or cost.get("aggregateCeilingUsdCents") != 1500
        or cost.get("authenticatedQuoteRequiredBeforeProvision") is not True
        or cost.get("spendAuthorized") is not False
    ):
        findings.append("cost")

    teardown = contract.get("teardown", {})
    if teardown.get("broadDeleteAllowed") is not False or teardown.get("cleanupEvidenceRequired") is not True:
        findings.append("teardown")

    science = contract.get("scientificBoundary", {})
    if science != {
        "frozenR3_325": "E-PASS / X-PASS / S-FAIL / C-NO-CLAIM",
        "rerunAllowed": False,
        "diagnosticIsScientificEvidence": False,
        "scientificClaimEstablished": False,
    }:
        findings.append("scientific_boundary")
    return tuple(sorted(set(findings)))


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the prepared VKE TLS EOF diagnostic contract")
    parser.add_argument("--contract", type=Path, default=CONTRACT_PATH)
    args = parser.parse_args()
    contract = load_contract(args.contract)
    findings = validate(contract)
    if findings:
        print("FAIL: " + ", ".join(findings))
        return 1
    print(json.dumps({"valid": True, "contractId": contract["contractId"], "contractDigest": canonical_digest(contract)}, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
