from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TRAVEL = ROOT / "contracts/provider/r4-410-travel-provider-human-gate-v2.json"
TRAVEL_APPROVAL = ROOT / "evidence/gates/R4-410/r4-410-human-approval-v1.json"
NOTIFICATION = ROOT / "contracts/product/r4-422-notification-human-gate-v1.json"
APPROVED_TRAVEL_DIGEST = "6d71059d2db366ce0ab3e54b7959f532346b0875101ebc1ab8da9189e8b3ac5c"
APPROVAL_STATEMENT = (
    "I approve R4-410 contract SHA-256 "
    f"{APPROVED_TRAVEL_DIGEST}, ratify HERE Technologies using HERE Routing API v8 "
    "and HERE Matrix Routing API v8 as the RouteMind candidate travel provider, "
    "accept that Japan-region Routing service access requires HERE confirmation and "
    "that processing is not Tokyo-region-pinned under the reviewed HERE contract/DPA/"
    "subprocessor locations, accept the synthetic Tokyo coordinate privacy boundary "
    "and billing ownership, and acknowledge that this approval authorizes zero account "
    "creation and zero live calls."
)


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
    if payload.get("schemaVersion") != 2 or payload.get("contractId") != "r4-410-travel-provider-human-gate-v2":
        findings.append("travel:identity")
    if payload.get("taskId") != "R4-410" or payload.get("status") != "PREPARED_TRAVEL_PROVIDER_HUMAN_GATE":
        findings.append("travel:status")

    selection = payload.get("selection", {})
    if (
        selection.get("recommendedCandidate") != "HERE_ROUTING_V8_AND_MATRIX_ROUTING_V8"
        or selection.get("selectedProvider") != "UNAPPROVED"
        or selection.get("providerValidated") is not False
        or selection.get("japanServiceEligibility") != "UNCONFIRMED_REQUIRES_HERE"
        or selection.get("processingRegion") != "NOT_REGION_PINNED"
    ):
        findings.append("travel:selection_fail_closed")
    provider = payload.get("recommendedProvider", {})
    products = provider.get("products", {})
    point = products.get("point", {})
    matrix = products.get("matrix", {})
    capabilities = provider.get("documentedCapabilities", {})
    if provider.get("provider") != "HERE_TECHNOLOGIES" or provider.get("validated") is not False:
        findings.append("travel:provider_claim")
    if point != {
        "product": "HERE_ROUTING_API_V8",
        "method": "GET",
        "endpoint": "https://router.hereapi.com/v8/routes",
    } or matrix != {
        "product": "HERE_MATRIX_ROUTING_API_V8",
        "method": "POST",
        "endpoint": "https://matrix.router.hereapi.com/v8/matrix",
        "boundedValidationMode": "synchronous_async_false",
    }:
        findings.append("travel:products")
    if not all(capabilities.get(name) is True for name in ("pointRouting", "matrixRouting", "timeAwareRouting", "distanceAndDuration")):
        findings.append("travel:capabilities")
    if capabilities.get("documentedMaximumOrigins") != 10000 or capabilities.get("documentedMaximumDestinations") != 10000:
        findings.append("travel:matrix_boundary")
    if capabilities.get("japanRegionAccessRestricted") is not True:
        findings.append("travel:japan_access")
    mandatory_findings = {
        "HERE documentation states that Routing service access in the Japan region is restricted and requires contacting HERE",
        "HERE documentation does not guarantee that Tokyo coordinate data is processed or retained only in Tokyo",
        "HERE DPA permits storage or processing in a country different from where the service is provided",
        "HERE subprocessor locations include multiple countries and may change",
    }
    if set(provider.get("mandatoryHumanFindings", [])) != mandatory_findings:
        findings.append("travel:processing_findings")
    if any(not str(source).startswith("https://") for source in provider.get("officialSources", [])) or len(provider.get("officialSources", [])) < 7:
        findings.append("travel:official_sources")

    request = payload.get("requestContract", {})
    if (
        request.get("timeoutMilliseconds") != 1500
        or request.get("maxRetries") != 1
        or request.get("invalidOrPartialMatrix") != "fail_closed_then_explicit_local_fallback"
        or request.get("asynchronousMatrixRedirects") != "forbidden_in_bounded_live_validation"
    ):
        findings.append("travel:bounded_request")
    privacy = payload.get("privacy", {})
    if set(privacy.get("outboundAllowlist", [])) != {"coordinates", "departure_time", "transport_mode", "derived_region_definition", "opaque_request_id"}:
        findings.append("travel:privacy_allowlist")
    if not {"tenant_id", "principal_id", "order_id", "courier_id", "phone", "email"}.issubset(set(privacy.get("outboundForbidden", []))):
        findings.append("travel:privacy_forbidden")
    if (
        privacy.get("processingRegion") != "NOT_REGION_PINNED"
        or privacy.get("tokyoResidencyGuaranteed") is not False
        or privacy.get("crossBorderProcessingPossible") is not True
    ):
        findings.append("travel:processing_region")
    credentials = payload.get("credentials", {})
    if (
        credentials.get("requiredNow") != []
        or credentials.get("requiredForLaterLiveValidation") != ["ROUTEMIND_TRAVEL_PROVIDER_API_KEY"]
        or credentials.get("queryLogging") != "forbidden"
        or {credentials.get("git"), credentials.get("logs"), credentials.get("evidence"), credentials.get("chat")} != {"forbidden"}
    ):
        findings.append("travel:credentials")
    fallback = payload.get("fallback", {})
    if (
        fallback.get("provider") != "deterministic-local"
        or fallback.get("semantics") != "external_fail_closed_then_explicit_local_fallback"
        or fallback.get("failOpen") is not False
        or fallback.get("alwaysAvailable") is not True
        or fallback.get("fallbackResultMayBeRepresentedAsProviderTruth") is not False
        or fallback.get("fallbackProvenanceRequired") is not True
    ):
        findings.append("travel:fallback")
    bounded = payload.get("boundedLiveValidation", {})
    if bounded != {
        "authorized": False,
        "allowedCallsAtThisGate": 0,
        "maximumDurationMinutesIfSeparatelyAuthorized": 30,
        "maximumPointCallsIfSeparatelyAuthorized": 20,
        "maximumMatrixRequestsIfSeparatelyAuthorized": 5,
        "maximumMatrixElementsIfSeparatelyAuthorized": 100,
        "maximumSpendUsdCentsIfSeparatelyAuthorized": 100,
        "newExecutionContractRequired": True,
        "japanServiceEligibilityRequired": True,
        "credentialRequired": True,
    }:
        findings.append("travel:execution_boundary")
    human_gate = payload.get("humanGate", {})
    required_approvals = {
        "HERE_PROVIDER_SELECTION",
        "HERE_ROUTING_AND_MATRIX_PRODUCTS",
        "HERE_JAPAN_SERVICE_ELIGIBILITY_PATH",
        "HERE_CONTRACT_AND_DPA",
        "NON_REGION_PINNED_PROCESSING",
        "SYNTHETIC_TOKYO_COORDINATE_PRIVACY",
        "ACCOUNT_AND_BILLING_OWNERSHIP",
    }
    if (
        set(human_gate.get("requiredApprovals", [])) != required_approvals
        or human_gate.get("requiredSecretNamesNow") != []
        or human_gate.get("requiredSecretNamesForLaterLiveValidation") != ["ROUTEMIND_TRAVEL_PROVIDER_API_KEY"]
        or human_gate.get("approvalDoesNotAuthorizeLiveCalls") is not True
        or human_gate.get("approvalDoesNotAuthorizeAccountCreation") is not True
        or human_gate.get("approvalDoesNotClaimJapanAccess") is not True
    ):
        findings.append("travel:human_gate")
    required_evidence = {
        "HERE_account_and_application_identity_without_secrets",
        "Japan_service_eligibility_confirmation",
        "contract_DPA_and_non_region_pinned_processing_acceptance",
        "documented_and_observed_point_product_semantics",
        "documented_and_observed_matrix_product_semantics",
        "time_context_units_and_synthetic_fixture_identity",
        "quota_timeout_error_and_partial_matrix_behavior",
        "deterministic_fallback_transition_and_provenance",
        "privacy_and_secret_leakage_scan",
        "actual_or_conservative_cost",
        "timestamps_versions_and_artifact_digests",
    }
    if set(payload.get("evidenceContract", [])) != required_evidence:
        findings.append("travel:evidence_contract")
    claims = payload.get("claims", {})
    if claims != {
        "providerSelected": False,
        "providerValidated": False,
        "japanServiceEligibilityValidated": False,
        "tokyoDataResidencyClaimed": False,
        "productionValidated": False,
        "localFallbackValidated": True,
    }:
        findings.append("travel:claims")
    return sorted(set(findings))


def validate_travel_approval(
    payload: dict[str, Any], travel: dict[str, Any]
) -> list[str]:
    findings: list[str] = []
    if (
        payload.get("schemaVersion") != 1
        or payload.get("approvalId") != "r4-410-travel-provider-human-approval-v1"
        or payload.get("taskId") != "R4-410"
        or payload.get("approvalStatus") != "HUMAN_APPROVED_CONTRACT_FROZEN"
        or payload.get("approvalSource") != "USER_EXPLICIT_INSTRUCTION"
    ):
        findings.append("travel_approval:identity")
    if (
        payload.get("approvedContractId") != travel.get("contractId")
        or payload.get("approvedCanonicalSha256") != APPROVED_TRAVEL_DIGEST
        or digest(travel) != APPROVED_TRAVEL_DIGEST
        or payload.get("approvalStatement") != APPROVAL_STATEMENT
    ):
        findings.append("travel_approval:contract_binding")
    if payload.get("approvalDate") != "2026-08-27":
        findings.append("travel_approval:date")
    if payload.get("ratification") != {
        "candidateProvider": "HERE_TECHNOLOGIES",
        "pointProduct": "HERE_ROUTING_API_V8",
        "matrixProduct": "HERE_MATRIX_ROUTING_API_V8",
        "japanServiceEligibility": "UNCONFIRMED_REQUIRES_HERE",
        "processingRegion": "NOT_REGION_PINNED",
        "syntheticTokyoCoordinatePrivacyAccepted": True,
        "billingOwnershipAccepted": True,
    }:
        findings.append("travel_approval:ratification_boundary")
    if payload.get("authorization") != {
        "accountCreation": False,
        "credentialAcquisition": False,
        "secretConfiguration": False,
        "liveCalls": False,
        "maximumCalls": 0,
        "maximumSpendUsdCents": 0,
    }:
        findings.append("travel_approval:authorization_boundary")
    if payload.get("claims") != {
        "candidateProviderRatified": True,
        "providerLiveValidated": False,
        "japanServiceEligibilityValidated": False,
        "tokyoDataResidencyClaimed": False,
        "productionValidated": False,
    }:
        findings.append("travel_approval:claims")
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


def summary(
    travel: dict[str, Any],
    travel_approval: dict[str, Any],
    notification: dict[str, Any],
) -> dict[str, Any]:
    return {
        "valid": True,
        "travelContractId": travel["contractId"],
        "travelDigest": digest(travel),
        "travelCandidateProviderRatified": travel_approval["claims"][
            "candidateProviderRatified"
        ],
        "travelProviderLiveValidated": travel_approval["claims"][
            "providerLiveValidated"
        ],
        "travelLiveCallsAuthorized": travel["boundedLiveValidation"]["authorized"],
        "notificationContractId": notification["contractId"],
        "notificationDigest": digest(notification),
        "notificationProviderSelected": notification["claims"]["providerSelected"],
        "notificationRealSendAuthorized": notification["boundedRealSend"]["authorized"],
    }


def main() -> int:
    travel = load_contract(TRAVEL)
    travel_approval = load_contract(TRAVEL_APPROVAL)
    notification = load_contract(NOTIFICATION)
    findings = (
        validate_travel(travel)
        + validate_travel_approval(travel_approval, travel)
        + validate_notification(notification)
    )
    if findings:
        for finding in sorted(findings):
            print(f"ERROR: {finding}")
        return 1
    print(
        json.dumps(
            summary(travel, travel_approval, notification),
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
