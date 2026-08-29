"""Validate the bounded, preparation-only R4-422 SES diagnostic contract."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/provider/r4-422-aws-ses-third-single-send-diagnostic-v1.json"
CONTRACT_ID = "r4-422-aws-ses-third-single-send-diagnostic-v1"
PRIOR_DIGESTS = {
    "e942a04b080da7cf42645d757fec61a1fb67428b59da29f90c93227b06c7d660",
    "9c32cc9df3ac34e2a85f722ec2bcce6c64e9e5057a2f9e85e0e14656c082feaa",
}
PROVIDER_BOUNDARY_DIGEST = "0cc9bcf99a11e3a4f948693e818c1c497ea7e0e3314ce15cd76f0a973eda4ffb"
SHA256 = re.compile(r"^[0-9a-f]{64}$")


def load_contract(path: Path = CONTRACT) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"{path} must contain a JSON object")
    return value


def canonical_digest(value: Mapping[str, Any]) -> str:
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _exact(actual: object, expected: object, finding: str, findings: list[str]) -> None:
    if actual != expected:
        findings.append(finding)


def validate_contract(payload: Mapping[str, Any]) -> list[str]:
    findings: list[str] = []
    _exact(payload.get("schemaVersion"), 1, "schema_version", findings)
    _exact(payload.get("contractId"), CONTRACT_ID, "identity", findings)
    _exact(payload.get("taskId"), "R4-422", "task", findings)
    _exact(
        payload.get("status"),
        "PREPARED_AWS_SES_THIRD_SINGLE_SEND_DIAGNOSTIC_HUMAN_GATE",
        "status",
        findings,
    )
    _exact(payload.get("independentContract"), True, "independent_contract", findings)

    dependencies = payload.get("frozenDependencies", {})
    _exact(dependencies.get("providerBoundarySha256"), PROVIDER_BOUNDARY_DIGEST, "provider_boundary", findings)
    prior = dependencies.get("priorConsumedContracts", [])
    prior_digests = {item.get("sha256") for item in prior if isinstance(item, Mapping)}
    if prior_digests != PRIOR_DIGESTS or any(not SHA256.fullmatch(str(value)) for value in prior_digests):
        findings.append("prior_contract_inventory")
    if dependencies.get("priorContractsMustRemainUnchanged") is not True:
        findings.append("prior_contract_immutability")
    if dependencies.get("priorContractDigestReuse") is not False:
        findings.append("prior_digest_reuse")
    if dependencies.get("historicalEvidenceMutation") is not False:
        findings.append("historical_evidence_mutation")

    _exact(
        payload.get("provider"),
        {
            "name": "AWS_SES",
            "channel": "EMAIL",
            "region": "ap-northeast-1",
            "endpoint": "email.ap-northeast-1.amazonaws.com",
            "operation": "SendEmail",
            "forbiddenOperations": ["SendRawEmail", "SendBulkEmail", "SendBulkTemplatedEmail"],
            "sdk": "AWS_SDK_FOR_JAVA_V2",
            "credentialMechanism": "DefaultCredentialsProvider_only",
            "expectedProfile": "routemind-ses",
        },
        "provider_boundary",
        findings,
    )

    identities = payload.get("identities", {})
    for role, variable in {
        "sender": "ROUTEMIND_NOTIFICATION_SENDER",
        "recipient": "ROUTEMIND_NOTIFICATION_SYNTHETIC_RECIPIENT",
    }.items():
        identity = identities.get(role, {})
        _exact(identity.get("sourceEnvironmentVariable"), variable, f"{role}_source", findings)
        _exact(identity.get("valueInContract"), "forbidden", f"{role}_contract_value", findings)
        _exact(identity.get("valueInLogsEvidenceChat"), "forbidden", f"{role}_output_value", findings)
        _exact(identity.get("syntheticOnly"), True, f"{role}_synthetic", findings)
    _exact(identities.get("productionRecipients"), "forbidden", "production_recipient", findings)

    _exact(
        payload.get("scope"),
        {
            "syntheticOnly": True,
            "maximumSendEmailRequests": 1,
            "maximumMessages": 1,
            "maximumRecipients": 1,
            "maximumCcRecipients": 0,
            "maximumBccRecipients": 0,
            "maximumAttachments": 0,
            "maximumBulkOperations": 0,
            "maximumRetries": 0,
            "maximumDurationMinutes": 15,
            "maximumSpendUsdCents": 10,
            "accountCreationAuthorized": False,
            "resourceMutationAuthorized": False,
            "providerConfigurationMutationAuthorized": False,
            "iamMutationAuthorized": False,
            "productionAccessRequestAuthorized": False,
            "liveCallAuthorizedOnlyAfterHumanGate": True,
            "fallbackProvider": "forbidden",
            "fallbackCannotRepresentAwsTruth": True,
        },
        "scope_boundary",
        findings,
    )

    _exact(
        payload.get("executionPath"),
        {
            "configuration": "current RouteMind notification provider configuration",
            "requestConstruction": "AwsSesRequestFactory",
            "providerAdapter": "AwsSesNotificationProvider",
            "transport": "AWS SDK for Java v2 SesClient.sendEmail",
            "historicalAdHocHelperAllowed": False,
            "adapterEnabledByDefault": False,
            "sanitizedObservation": "AwsSesErrorObservation via AwsSesErrorObservationSink",
        },
        "hardened_execution_path",
        findings,
    )

    request = payload.get("requestBoundary", {})
    _exact(request.get("apiOperation"), "SendEmail", "operation", findings)
    for field, expected in {
        "sendEmailRequests": 1,
        "recipients": 1,
        "cc": 0,
        "bcc": 0,
        "attachments": 0,
        "bulkOperations": 0,
        "automaticRetries": 0,
        "retryPolicy": "none",
        "sendRawEmail": "forbidden",
        "endpointOverride": "forbidden",
        "regionOverride": "forbidden",
        "configurationSet": "absent",
        "tags": 0,
        "delegatedSendingAuthorization": "forbidden",
        "timeoutSeconds": 15,
    }.items():
        _exact(request.get(field), expected, f"request_{field}", findings)

    observation = payload.get("sanitizedErrorCapture", {})
    required_observation_fields = {
        "provider",
        "operation",
        "region",
        "exception_class",
        "safe_service_error_code",
        "http_status",
        "request_id_presence_or_redacted_representation",
        "normalized_provider_error_category",
        "sanitized_provider_semantic",
        "provider_acceptance",
        "request_count",
        "retry_count",
        "fallback_usage",
        "timestamp",
        "safe_request_shape",
    }
    if observation.get("required") is not True or set(observation.get("fields", [])) != required_observation_fields:
        findings.append("sanitized_observation_fields")
    for field in ("rawExceptionMessage", "rawProviderPayload", "rawRequest", "identityAndCredentialValues"):
        _exact(observation.get(field), "forbidden", f"observation_{field}", findings)

    consumption = payload.get("consumptionSemantics", {})
    _exact(consumption.get("consumedAfterSendEmailAttempt"), True, "consumption_after_attempt", findings)
    _exact(consumption.get("consumedAfterProviderResponse"), True, "consumption_after_response", findings)
    _exact(consumption.get("silentReuseAfterFailure"), False, "silent_reuse", findings)
    _exact(consumption.get("historicalContractsMayBeReused"), False, "historical_reuse", findings)
    _exact(consumption.get("subsequentAttempt"), "requires a new independent contract and Human Gate", "subsequent_contract", findings)

    evidence = payload.get("evidenceContract", {})
    if not str(evidence.get("preparationArtifact", "")).endswith("aws-ses-third-single-send-diagnostic-preparation-20260829.json"):
        findings.append("preparation_evidence")
    required_evidence_fields = {
        "contractSha256",
        "providerAndRegion",
        "configurationReadinessWithoutValues",
        "credentialChainReadinessWithoutValues",
        "hardenedAdapterAndRequestPath",
        "outboxAndOpaqueNotificationIdentity",
        "requestAndResponseTimestamps",
        "requestCountAndNoRetryOutcome",
        "providerAcceptanceMetadataRedactedOrDigested",
        "providerMessageIdIfReturnedRedactedOrDigested",
        "authenticatedDeliveryOrBounceOutcome",
        "sanitizedErrorObservationIfFailure",
        "privacyBoundaryAndSyntheticScope",
        "actualOrConservativeCost",
        "artifactSha256Digests",
        "secretLeakageScan",
        "negativeAndPartialResults",
    }
    if set(evidence.get("requiredFields", [])) != required_evidence_fields:
        findings.append("evidence_fields")
    _exact(evidence.get("secretHandling"), "no credential, sender, recipient, message body, raw provider token, or browser material may be persisted", "evidence_secrets", findings)

    claims = payload.get("claims", {})
    _exact(claims.get("liveCallsExecuted"), False, "live_calls_claim", findings)
    _exact(claims.get("syntheticSendValidated"), False, "send_claim", findings)
    _exact(claims.get("deliveryValidated"), False, "delivery_claim", findings)
    _exact(claims.get("productionValidated"), False, "production_claim", findings)
    _exact(claims.get("humanGateRequired"), True, "human_gate_required", findings)

    human_gate = payload.get("humanGate", {})
    required_approvals = set(human_gate.get("requiredApprovals", []))
    if human_gate.get("approvalRequired") is not True or human_gate.get("approvalAuthorizesNoActionBeforeExactDigestApproval") is not True:
        findings.append("human_gate_boundary")
    if "HISTORICAL_CONTRACTS_NOT_REUSED" not in required_approvals or "HARDENED_ROUTE_MIND_ADAPTER_PATH" not in required_approvals:
        findings.append("human_gate_scope")
    statement = str(human_gate.get("approvalStatementTemplate", ""))
    for token in ("R4-422", "AWS SES", "ap-northeast-1", "exactly one", "zero retries", "zero fallback", "USD 0.10", "15-minute", "hardened RouteMind", "historical R4-422 SES contracts"):
        if token not in statement:
            findings.append(f"human_gate_text:{token}")
    _exact(human_gate.get("credentialMechanism"), "AWS_SDK_DEFAULT_CREDENTIALS_PROVIDER_ONLY", "credential_mechanism", findings)

    serialized = json.dumps(payload, ensure_ascii=True)
    for forbidden in ("@", "AKIA", "arn:aws:", "secretAccessKey", "sessionToken", "authorization header"):
        if forbidden in serialized:
            findings.append("sensitive_contract_content")
    actual_digest = canonical_digest(payload)
    if actual_digest in PRIOR_DIGESTS or not SHA256.fullmatch(actual_digest):
        findings.append("digest_reuse_or_shape")
    return sorted(set(findings))


def main() -> None:
    contract = load_contract()
    findings = validate_contract(contract)
    if findings:
        raise SystemExit(json.dumps({"valid": False, "findings": findings}, separators=(",", ":")))
    print(
        json.dumps(
            {
                "valid": True,
                "contractId": contract["contractId"],
                "canonicalSha256": canonical_digest(contract),
                "externalRequests": 0,
                "awsMutations": 0,
                "liveExecutionAuthorized": False,
            },
            separators=(",", ":"),
        )
    )


if __name__ == "__main__":
    main()
