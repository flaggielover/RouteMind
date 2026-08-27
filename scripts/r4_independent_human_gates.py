from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TRAVEL = ROOT / "contracts/provider/r4-410-travel-provider-human-gate-v1.json"
NOTIFICATION = ROOT / "contracts/product/r4-422-notification-human-gate-v1.json"


def load_contract(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(f"{path.name} must contain a JSON object")
    return payload


def digest(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def validate_travel(payload: dict[str, Any]) -> list[str]:
    findings: list[str] = []
    if payload.get("schemaVersion") != 1 or payload.get("contractId") != "r4-410-travel-provider-human-gate-v1":
        findings.append("travel:identity")
    if payload.get("taskId") != "R4-410" or payload.get("status") != "PREPARED_TRAVEL_PROVIDER_HUMAN_GATE":
        findings.append("travel:status")

    selection = payload.get("selection", {})
    if selection.get("recommendedCandidate") != "HERE_MATRIX_ROUTING_V8" or selection.get("selectedProvider") != "UNAPPROVED" or selection.get("providerValidated") is not False:
        findings.append("travel:selection_fail_closed")
    provider = payload.get("recommendedProvider", {})
    capabilities = provider.get("documentedCapabilities", {})
    if provider.get("provider") != "HERE_MATRIX_ROUTING_V8" or provider.get("validated") is not False:
        findings.append("travel:provider_claim")
    if not all(capabilities.get(name) is True for name in ("pointRouting", "matrixRouting", "timeAwareRouting", "distanceAndDuration")):
        findings.append("travel:capabilities")
    if capabilities.get("documentedMaximumOrigins") != 10000 or capabilities.get("documentedMaximumDestinations") != 10000:
        findings.append("travel:matrix_boundary")
    if any(not str(source).startswith("https://") for source in provider.get("officialSources", [])) or len(provider.get("officialSources", [])) < 3:
        findings.append("travel:official_sources")

    request = payload.get("requestContract", {})
    if request.get("timeoutMilliseconds") != 1500 or request.get("maxRetries") != 1 or request.get("invalidOrPartialMatrix") != "fail_closed_then_local_fallback":
        findings.append("travel:bounded_request")
    privacy = payload.get("privacy", {})
    if set(privacy.get("outboundAllowlist", [])) != {"coordinates", "departure_time", "transport_mode", "opaque_request_id"}:
        findings.append("travel:privacy_allowlist")
    if not {"tenant_id", "principal_id", "order_id", "courier_id", "phone", "email"}.issubset(set(privacy.get("outboundForbidden", []))):
        findings.append("travel:privacy_forbidden")
    credentials = payload.get("credentials", {})
    if credentials.get("environmentVariable") != "ROUTEMIND_TRAVEL_PROVIDER_API_KEY" or {credentials.get("git"), credentials.get("logs"), credentials.get("evidence")} != {"forbidden"}:
        findings.append("travel:credentials")
    fallback = payload.get("fallback", {})
    if fallback.get("provider") != "deterministic-local" or fallback.get("alwaysAvailable") is not True or fallback.get("fallbackResultMayBeRepresentedAsProviderTruth") is not False:
        findings.append("travel:fallback")
    bounded = payload.get("boundedLiveValidation", {})
    if bounded != {
        "authorized": False,
        "maximumDurationMinutes": 30,
        "maximumPointCalls": 20,
        "maximumMatrixRequests": 5,
        "maximumMatrixElements": 100,
        "maximumSpendUsdCents": 100,
        "newExecutionContractRequired": True,
    }:
        findings.append("travel:execution_boundary")
    claims = payload.get("claims", {})
    if claims != {"providerSelected": False, "providerValidated": False, "productionValidated": False, "localFallbackValidated": True}:
        findings.append("travel:claims")
    return sorted(set(findings))


def validate_notification(payload: dict[str, Any]) -> list[str]:
    findings: list[str] = []
    if payload.get("schemaVersion") != 1 or payload.get("contractId") != "r4-422-notification-human-gate-v1":
        findings.append("notification:identity")
    if payload.get("taskId") != "R4-422" or payload.get("status") != "PREPARED_NOTIFICATION_PROVIDER_HUMAN_GATE" or payload.get("semanticsContract") != "r4-420-product-semantics-v1":
        findings.append("notification:status")

    selection = payload.get("selection", {})
    if selection.get("recommendedCandidate") != "AWS_SES_EMAIL_AP_NORTHEAST_1" or selection.get("selectedProvider") != "UNAPPROVED" or selection.get("selectedChannel") != "UNAPPROVED" or selection.get("providerValidated") is not False:
        findings.append("notification:selection_fail_closed")
    provider = payload.get("recommendedProvider", {})
    if provider.get("provider") != "AWS_SES" or provider.get("region") != "ap-northeast-1" or provider.get("endpoint") != "email.ap-northeast-1.amazonaws.com" or provider.get("validated") is not False:
        findings.append("notification:provider_claim")
    if any(not str(source).startswith("https://") for source in provider.get("officialSources", [])) or len(provider.get("officialSources", [])) < 4:
        findings.append("notification:official_sources")

    local = payload.get("localImplementationBoundary", {})
    required_local = {
        "durableOwner": "java_business_api",
        "durableStore": "postgresql",
        "intentCreation": "same_transaction_outbox",
        "delivery": "asynchronous_idempotent_worker",
        "consentRecheck": "before_every_attempt",
        "providerAcceptanceIsDelivery": False,
        "deliveryRequires": "authenticated_provider_delivery_receipt",
        "maxAttempts": 5,
        "realAdapterDefault": "disabled",
    }
    if any(local.get(key) != value for key, value in required_local.items()):
        findings.append("notification:local_boundary")
    credentials = payload.get("credentials", {})
    if set(credentials.get("environmentVariables", [])) != {"AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN"} or {credentials.get("git"), credentials.get("logs"), credentials.get("evidence")} != {"forbidden"}:
        findings.append("notification:credentials")
    identities = payload.get("identityAndRecipients", {})
    if (
        identities.get("senderIdentity") != "UNAPPROVED_EXTERNAL_VALUE"
        or identities.get("syntheticRecipient") != "UNAPPROVED_EXTERNAL_VALUE"
        or identities.get("senderEnvironmentVariable") != "ROUTEMIND_NOTIFICATION_SENDER"
        or identities.get("syntheticRecipientEnvironmentVariable")
        != "ROUTEMIND_NOTIFICATION_SYNTHETIC_RECIPIENT"
        or identities.get("productionRecipients") != "forbidden"
    ):
        findings.append("notification:recipient_boundary")
    network = payload.get("networkAndPrivacy", {})
    if network.get("providerRegion") != "ap-northeast-1" or network.get("publicInboundRouteMindEndpoint") is not False or network.get("callbackAuthenticationRequired") is not True:
        findings.append("notification:network_boundary")
    if not {"recipient", "sender", "message_body", "credentials", "provider_message_id"}.issubset(set(network.get("telemetryForbidden", []))):
        findings.append("notification:privacy")
    bounded = payload.get("boundedRealSend", {})
    if bounded != {
        "authorized": False,
        "maximumDurationMinutes": 30,
        "maximumMessages": 10,
        "maximumSpendUsdCents": 100,
        "newExecutionContractRequired": True,
        "accountOrResourceCreationAuthorized": False,
    }:
        findings.append("notification:execution_boundary")
    required_failures = {"no_consent_suppressed", "quiet_hours_deferred_then_rechecked", "duplicate_intent_idempotent", "retryable_failure_bounded", "retry_exhaustion_terminal", "provider_acceptance_not_delivery", "authenticated_delivery_receipt", "authenticated_bounce_receipt", "unauthenticated_callback_rejected", "opt_out_before_retry_suppressed"}
    if set(payload.get("failureMatrix", [])) != required_failures:
        findings.append("notification:failure_matrix")
    claims = payload.get("claims", {})
    if claims != {"providerSelected": False, "providerValidated": False, "realMessageSent": False, "deliveryValidated": False, "productionValidated": False}:
        findings.append("notification:claims")
    return sorted(set(findings))


def summary(travel: dict[str, Any], notification: dict[str, Any]) -> dict[str, Any]:
    return {
        "valid": True,
        "travelContractId": travel["contractId"],
        "travelDigest": digest(travel),
        "travelProviderSelected": travel["claims"]["providerSelected"],
        "travelLiveCallsAuthorized": travel["boundedLiveValidation"]["authorized"],
        "notificationContractId": notification["contractId"],
        "notificationDigest": digest(notification),
        "notificationProviderSelected": notification["claims"]["providerSelected"],
        "notificationRealSendAuthorized": notification["boundedRealSend"]["authorized"],
    }


def main() -> int:
    travel = load_contract(TRAVEL)
    notification = load_contract(NOTIFICATION)
    findings = validate_travel(travel) + validate_notification(notification)
    if findings:
        for finding in sorted(findings):
            print(f"ERROR: {finding}")
        return 1
    print(json.dumps(summary(travel, notification), sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
