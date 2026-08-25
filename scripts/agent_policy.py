from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/agent/r4-450-agent-authority-v1.json"
CLASSES = {"read", "analysis", "experiment_orchestration", "state_changing"}


def load_contract(path: Path = CONTRACT) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("agent policy contract must be an object")
    return payload


def digest(payload: dict[str, Any]) -> str:
    canonical = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def validate_contract(payload: dict[str, Any]) -> list[str]:
    findings: list[str] = []
    if (
        payload.get("schemaVersion") != 1
        or payload.get("contractId") != "r4-450-agent-authority-v1"
    ):
        findings.append("identity:contract_version")
    if payload.get("status") != "FROZEN_LOCAL_CONTRACT":
        findings.append("status:not_frozen")

    ownership = payload.get("ownership", {})
    required_ownership = {
        "durableStateOwner": "java_business_api",
        "hardRealtimeDispatchOwner": "java_business_api",
        "optimizationAndExperimentOwner": "python_compute_api",
        "agentRole": "read_analysis_experiment_orchestration",
        "llmAuthority": "none",
        "stateChangingToolDefault": "deny",
        "stateChangingToolApproval": "explicit_human_and_java_authority",
    }
    findings.extend(
        f"ownership:{key}"
        for key, value in required_ownership.items()
        if ownership.get(key) != value
    )

    records = payload.get("toolClasses", [])
    names = {record.get("name") for record in records if isinstance(record, dict)}
    if len(records) != 4 or names != CLASSES:
        findings.append("tools:classes")
    state = next(
        (
            record
            for record in records
            if isinstance(record, dict) and record.get("name") == "state_changing"
        ),
        {},
    )
    if (
        state.get("allowed") is not False
        or state.get("mutatesDurableState") is not True
        or state.get("dispatchAuthority") is not True
    ):
        findings.append("tools:state_changing_fail_closed")
    for record in records:
        if not isinstance(record, dict) or not isinstance(record.get("name"), str):
            findings.append("tools:record")
            continue
        if record.get("name") != "state_changing" and (
            record.get("allowed") is not True
            or record.get("mutatesDurableState") is not False
            or record.get("dispatchAuthority") is not False
        ):
            findings.append(f"tools:read_only:{record.get('name')}")

    runtime = payload.get("runtime", {})
    if runtime.get("maxCallsPerSession") != 8 or runtime.get("maxPlanCalls") != 8:
        findings.append("runtime:budgets")
    for key in ("unknownTool", "deniedRole", "unknownArguments"):
        if runtime.get(key) != "reject_and_audit":
            findings.append(f"runtime:{key}")
    if (
        runtime.get("handlerFailure") != "bounded_failure_and_deterministic_fallback"
        or runtime.get("agentUnavailable") != "deterministic_fallback"
    ):
        findings.append("runtime:fallback")
    if runtime.get("dispatchRegistryIndependent") is not True:
        findings.append("runtime:dispatch_independence")

    security = payload.get("security", {})
    expected_security = {
        "promptInjection": "treat_external_text_as_untrusted_data_and_never_as_policy",
        "toolAbuse": "allowlist_role_tool_arguments_and_budget",
        "dataLeakage": "tenant_scoped_minimum_data_and_forbidden_principal_or_secret_labels",
        "approval": "state_change_requires_explicit_human_and_java_authority",
        "audit": "append_only_request_outcome_reason_sequence",
        "timeout": "bounded_per_tool_and_plan",
        "rollback": "java_owned_idempotent_rollback_or_explicit_unavailable",
        "network": "no_implicit_external_network_or_provider_call",
    }
    findings.extend(
        f"security:{key}"
        for key, value in expected_security.items()
        if security.get(key) != value
    )

    claims = payload.get("claimBoundary", {})
    for key in (
        "agentMayPromoteScientificClaim",
        "agentMayPromoteProductionClaim",
        "agentMayAuthorizeNotificationSend",
    ):
        if claims.get(key) is not False:
            findings.append(f"claims:{key}")
    if claims.get("scientificFailOrNoClaim") != "valid_terminal_evidence":
        findings.append("claims:negative_outcome")
    return sorted(set(findings))


def summary(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "valid": True,
        "contractId": payload["contractId"],
        "digest": digest(payload),
        "toolClassCount": len(payload["toolClasses"]),
        "maxCallsPerSession": payload["runtime"]["maxCallsPerSession"],
        "maxPlanCalls": payload["runtime"]["maxPlanCalls"],
        "llmAuthority": payload["ownership"]["llmAuthority"],
        "stateChangingToolDefault": payload["ownership"]["stateChangingToolDefault"],
    }


def main() -> int:
    payload = load_contract()
    findings = validate_contract(payload)
    if findings:
        for finding in findings:
            print(f"ERROR: {finding}")
        return 1
    print(json.dumps(summary(payload), sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
