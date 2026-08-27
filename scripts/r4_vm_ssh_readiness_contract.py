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
CONTRACT = ROOT / "contracts/external-validation/r4-vultr-tokyo-vm-ssh-readiness-diagnostic-v1.json"
IAC_ROOT = ROOT / "infra/external-validation/vultr-tokyo-vm-ssh-readiness-v1"
EXPECTED_FINGERPRINT = "SHA256:JHiQkjaVyp5ft91S12iyyCbDB6PCAGhDqYTVnMJAUeI"
EXPECTED_STAGES = [
    "VM_CREATED",
    "PUBLIC_IP_ASSIGNED",
    "TCP22_REACHABLE",
    "SSH_BANNER_RECEIVED",
    "SSH_KEX_STARTED",
    "SSH_HOST_KEY_VERIFIED",
    "SSH_AUTH_STARTED",
    "SSH_AUTHENTICATED",
    "CLOUD_INIT_COMPLETE",
    "ROUTEMIND_BOOTSTRAP_READY",
]


class SshReadinessContractError(ValueError):
    pass


def load_contract(path: Path = CONTRACT) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SshReadinessContractError(f"cannot load contract: {path}") from exc
    if not isinstance(value, dict):
        raise SshReadinessContractError("contract root must be an object")
    return value


def canonical_digest(contract: Mapping[str, Any]) -> str:
    payload = json.dumps(contract, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def validate_contract(contract: Mapping[str, Any]) -> tuple[str, ...]:
    findings: list[str] = []
    if contract.get("contractId") != "r4-vultr-tokyo-vm-ssh-readiness-diagnostic-v1":
        findings.append("contract_id")
    if contract.get("status") != "PREPARED_NOT_APPROVED_NOT_EXECUTED":
        findings.append("status")

    freeze = _mapping(contract.get("historicalFreeze"))
    if (
        freeze.get("vmV2Result") != "FAIL_CLOSED_AT_SECURE_BOOTSTRAP"
        or freeze.get("retainedVultrResources") != 0
        or freeze.get("vmV2ConservativeCostUsdCents") != 24.6
        or freeze.get("cumulativeConservativeExternalCostUsdCents") != 1124.6
        or freeze.get("rootCause") != "UNKNOWN"
        or freeze.get("historicalEvidenceImmutable") is not True
    ):
        findings.append("historical_freeze")

    approval = _mapping(contract.get("approvalBoundary"))
    if (
        approval.get("provider") != "Vultr"
        or approval.get("region") != "nrt"
        or approval.get("requiredHumanGate") != "ROUTEMIND TOKYO VM SSH-READINESS HUMAN GATE"
        or approval.get("oldDigestReuseAllowed") is not False
        or any(
            approval.get(field) is not False
            for field in (
                "resourceCreationAuthorized",
                "spendAuthorized",
                "liveMutationCallsAuthorized",
                "terraformApplyAuthorized",
            )
        )
    ):
        findings.append("approval_boundary")

    infrastructure = _mapping(contract.get("infrastructure"))
    resources = infrastructure.get("resources")
    expected_counts = {
        "vultr_firewall_group": 1,
        "vultr_firewall_rule": 1,
        "vultr_instance": 1,
        "vultr_vpc": 0,
    }
    if (
        not isinstance(resources, list)
        or len(resources) != 1
        or _mapping(resources[0]).get("plan") != "vc2-1c-1gb"
        or _mapping(resources[0]).get("region") != "nrt"
        or _mapping(resources[0]).get("imageId") != 2284
        or _mapping(resources[0]).get("expectedSshUsername") != "root"
        or _mapping(infrastructure.get("terraformResourceCounts")) != expected_counts
        or infrastructure.get("maximumRuntimeMinutes") != 60
        or any(
            infrastructure.get(field) is not False
            for field in (
                "routeMindDeploymentAllowed",
                "signozDeploymentAllowed",
                "packageInstallationAllowed",
                "hostRebootAllowed",
                "sshdOrNetworkRestartAllowed",
            )
        )
    ):
        findings.append("infrastructure")

    network = _mapping(contract.get("network"))
    expected_rule = {
        "id": "operator-ssh",
        "source": "ROUTEMIND_OPERATOR_CIDR",
        "subnetSize": 32,
        "protocol": "tcp",
        "port": 22,
    }
    if (
        network.get("publicIngressRules") != [expected_rule]
        or set(network.get("forbiddenCidrs", [])) != {"0.0.0.0/0", "::/0"}
        or any(network.get(field) != 0 for field in ("publicHttpEndpoints", "publicApplicationEndpoints", "publicOtlpEndpoints"))
    ):
        findings.append("network")

    identity = _mapping(contract.get("sshIdentity"))
    if (
        identity.get("expectedPublicKeySha256") != EXPECTED_FINGERPRINT
        or identity.get("publicKeyType") != "ED25519"
        or identity.get("imageExpectedUsername") != "root"
        or identity.get("terraformUserScheme") != "root"
        or "ssh-keyscan" not in str(identity.get("hostKeyPinningProcedure", ""))
        or "StrictHostKeyChecking=yes" not in str(identity.get("hostKeyPinningProcedure", ""))
        or any(
            identity.get(field) is not True
            for field in (
                "privateKeyMustBeOutsideRepository",
                "providerPublicKeyFingerprintMustMatch",
                "strictHostKeyCheckingRequired",
            )
        )
        or identity.get("acceptNewAllowed") is not False
        or identity.get("passwordAuthenticationAllowed") is not False
    ):
        findings.append("ssh_identity")

    machine = _mapping(contract.get("readinessStateMachine"))
    if (
        machine.get("orderedStages") != EXPECTED_STAGES
        or machine.get("tcpOkIsSufficient") is not False
        or machine.get("successRequiresEveryStage") is not True
        or machine.get("rootCauseOnIncompleteEvidence") != "UNKNOWN"
    ):
        findings.append("state_machine")

    polling = _mapping(contract.get("polling"))
    phases = polling.get("phases", [])
    if (
        polling.get("maximumRuntimeMinutes") != 60
        or sum(_mapping(item).get("maximumMinutes", 0) for item in phases) != 60
        or polling.get("unboundedRetryAllowed") is not False
        or polling.get("automaticRebootAllowed") is not False
    ):
        findings.append("polling")

    guest = _mapping(contract.get("guestReadiness"))
    if (
        guest.get("atomicWriteRequired") is not True
        or any(
            guest.get(field) is not False
            for field in (
                "packageUpdate",
                "packageUpgrade",
                "sshdMutation",
                "authorizedKeysMutation",
                "networkMutation",
                "reboot",
            )
        )
    ):
        findings.append("guest_readiness")

    independence = _mapping(contract.get("artifactIndependence"))
    if (
        independence.get("rawBeforeAggregation") is not True
        or independence.get("perTargetAtomicWrite") is not True
        or independence.get("oneTargetFailureMayBlockOtherTarget") is not False
        or independence.get("aggregationMayDeleteRaw") is not False
    ):
        findings.append("artifact_independence")

    matrix = contract.get("rootCauseMatrix")
    if (
        not isinstance(matrix, list)
        or [item.get("id") for item in matrix if isinstance(item, Mapping)] != list("ABCDEFGHIJKLMNOP")
        or any(
            not all(field in item for field in ("candidate", "support", "contradiction", "confidence", "discriminatingTest"))
            for item in matrix
            if isinstance(item, Mapping)
        )
    ):
        findings.append("root_cause_matrix")

    cost = _mapping(contract.get("cost"))
    if (
        cost.get("hourlyUsdCents") != 0.7
        or cost.get("incrementalExecutionCeilingUsdCents") != 100
        or cost.get("cumulativeConservativeBeforeUsdCents") != 1124.6
        or cost.get("authenticatedQuoteRequiredBeforeApply") is not True
        or cost.get("spendAuthorized") is not False
    ):
        findings.append("cost")

    evidence = _mapping(contract.get("evidenceContract"))
    if (
        evidence.get("timestampsMustBeUtc") is not True
        or evidence.get("artifactSha256Required") is not True
        or evidence.get("secretValuesForbidden") is not True
        or evidence.get("mockEvidenceAcceptedAsExternal") is not False
        or evidence.get("tcpOkAcceptedAsSshReady") is not False
        or evidence.get("diagnosticMayPromoteR4_405OrR4_406") is not False
    ):
        findings.append("evidence_contract")

    teardown = _mapping(contract.get("teardown"))
    if (
        teardown.get("alwaysAttemptAfterCreate") is not True
        or teardown.get("broadDeleteAllowed") is not False
        or teardown.get("retainResourcesAllowed") is not False
        or len(teardown.get("ownedResources", [])) != 3
    ):
        findings.append("teardown")

    automation = _mapping(contract.get("automation"))
    if (
        automation.get("iacRoot") != "infra/external-validation/vultr-tokyo-vm-ssh-readiness-v1"
        or automation.get("defaultAction") != "OFFLINE_ONLY"
        or automation.get("terraformApplyAvailableInPreparationAutomation") is not False
        or automation.get("mutatingActionsRequireFreshHumanGate") is not True
    ):
        findings.append("automation")

    scientific = _mapping(contract.get("scientificBoundary"))
    if (
        scientific.get("frozenR3_325") != "E-PASS / X-PASS / S-FAIL / C-NO-CLAIM"
        or scientific.get("rerunAllowed") is not False
        or scientific.get("externalDiagnosticIsScientificEvidence") is not False
        or scientific.get("scientificClaimEstablished") is not False
    ):
        findings.append("scientific_boundary")
    return tuple(sorted(set(findings)))


def validate_iac(root: Path = IAC_ROOT) -> tuple[str, ...]:
    findings: list[str] = []
    required = {"versions.tf", "variables.tf", "main.tf", "outputs.tf", "cloud-init.yaml.tftpl"}
    if missing := sorted(name for name in required if not (root / name).is_file()):
        return ("iac_missing:" + ",".join(missing),)
    terraform = "\n".join(
        (root / name).read_text(encoding="utf-8")
        for name in ("versions.tf", "variables.tf", "main.tf", "outputs.tf")
    )
    counts = Counter(re.findall(r'resource\s+"([a-z0-9_]+)"\s+"', terraform))
    if counts != Counter({"vultr_firewall_group": 1, "vultr_firewall_rule": 1, "vultr_instance": 1}):
        findings.append("terraform_resource_inventory")
    required_fragments = (
        'plan                       = "vc2-1c-1gb"',
        'region                     = "nrt"',
        "ubuntu_24_04_x64_os_id     = 2284",
        'expected_ssh_username      = "root"',
        f'expected_public_key_sha256 = "{EXPECTED_FINGERPRINT}"',
        "subnet_size       = 32",
        'port              = "22"',
        "vpc_ids           = []",
        'backups           = "disabled"',
        "enable_ipv6       = false",
    )
    for fragment in required_fragments:
        if terraform.count(fragment) != 1:
            findings.append("terraform_boundary:" + fragment.split("=")[0].strip())
    for forbidden in (
        "vultr_vpc",
        "vultr_kubernetes",
        "vultr_load_balancer",
        "vultr_block_storage",
        'subnet = "0.0.0.0"',
        "subnet_size = 0",
    ):
        if forbidden in terraform:
            findings.append("terraform_forbidden:" + forbidden)

    cloud = (root / "cloud-init.yaml.tftpl").read_text(encoding="utf-8")
    if "\r\n" in cloud:
        findings.append("cloud_init_crlf")
    for required_fragment in (
        "#cloud-config\n",
        "package_update: false",
        "package_upgrade: false",
        "ssh_pwauth: false",
        "disable_root: false",
        "#!/usr/bin/env python3",
        "POST_CLOUD_INIT",
    ):
        if required_fragment not in cloud:
            findings.append("cloud_init_required:" + required_fragment.strip())
    for forbidden in (
        "apt ",
        "apt-get",
        "packages:",
        "reboot",
        "shutdown",
        "systemctl restart ssh",
        "systemctl restart network",
        "authorized_keys\n",
    ):
        if forbidden in cloud:
            findings.append("cloud_init_forbidden:" + forbidden.strip())
    return tuple(sorted(set(findings)))


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the Tokyo VM SSH-readiness contract")
    parser.add_argument("--contract", type=Path, default=CONTRACT)
    parser.add_argument("--skip-iac", action="store_true")
    arguments = parser.parse_args()
    try:
        contract = load_contract(arguments.contract)
        findings = list(validate_contract(contract))
        if not arguments.skip_iac:
            findings.extend(validate_iac())
    except SshReadinessContractError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    if findings:
        print("FAIL: " + ", ".join(sorted(set(findings))))
        return 1
    print(
        json.dumps(
            {
                "valid": True,
                "contractId": contract["contractId"],
                "canonicalSha256": canonical_digest(contract),
                "status": contract["status"],
                "region": contract["approvalBoundary"]["region"],
                "resourceCreationAuthorized": False,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
