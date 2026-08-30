"""Validate the offline-only R4-422 Gmail refresh-if-required single-send contract."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/provider/r4-422-google-gmail-refresh-if-required-single-send-v1.json"
EXPECTED_DIGEST = "35702d6d6698b78f08757b2560deb2bfee50503d0b8cc90b8fd2fcdf9431535f"
HISTORICAL_CONTRACTS = [
    "contracts/provider/r4-422-google-gmail-live-validation-v1.json",
    "contracts/provider/r4-422-google-gmail-oauth-bootstrap-v1.json",
    "contracts/provider/r4-422-google-gmail-oauth-bootstrap-v2.json",
    "contracts/provider/r4-422-google-gmail-oauth-password-remote-forward-v1.json",
    "contracts/provider/r4-422-google-gmail-oauth-remote-forward-bootstrap-v1.json",
    "contracts/provider/r4-422-google-gmail-single-send-validation-v1.json",
    "contracts/provider/r4-422-google-gmail-single-send-validation-v2.json",
    "contracts/provider/r4-422-google-gmail-token-refresh-recovery-v1.json",
]


def canonical_digest(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _strings(value: Any) -> list[str]:
    if isinstance(value, dict):
        return [item for child in value.values() for item in _strings(child)]
    if isinstance(value, list):
        return [item for child in value for item in _strings(child)]
    return [value] if isinstance(value, str) else []


def validate(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if canonical_digest(payload) != EXPECTED_DIGEST:
        errors.append("contract digest mismatch")

    identity = {key: payload.get(key) for key in ("schemaVersion", "contractId", "taskId", "status", "provider", "api", "operation", "channel")}
    if identity != {
        "schemaVersion": 1,
        "contractId": "r4-422-google-gmail-refresh-if-required-single-send-v1",
        "taskId": "R4-422",
        "status": "PREPARED_GOOGLE_GMAIL_REFRESH_IF_REQUIRED_SINGLE_SEND_HUMAN_GATE",
        "provider": "GOOGLE_GMAIL",
        "api": "Gmail API v1",
        "operation": "users.messages.send",
        "channel": "EMAIL",
    }:
        errors.append("contract identity drifted")

    auth = payload.get("authentication", {})
    if {
        auth.get("scope"), auth.get("credentialSource"), auth.get("credentialEnvironmentVariable"),
        auth.get("expectedOauthUserId"), auth.get("oauthSessionsAuthorized"),
        auth.get("tokenExchangesAuthorized"), auth.get("credentialRefreshesAuthorized"),
        auth.get("browserLoginAuthorized"), auth.get("sshAuthorized"),
    } != {
        "https://www.googleapis.com/auth/gmail.send", "EXTERNAL_WINDOWS_OAUTH_TOKEN_STORE",
        "ROUTEMIND_GMAIL_TOKEN_STORE", "default", 0, 0, 1, False, False,
    }:
        errors.append("authentication boundary drifted")

    historical = payload.get("historicalContracts", {})
    if historical.get("reuse") != "FORBIDDEN" or historical.get("allConsumedAndImmutable") is not True:
        errors.append("historical reuse boundary drifted")
    if historical.get("nonReusable") != HISTORICAL_CONTRACTS:
        errors.append("historical contract inventory drifted")
    if any(not (ROOT / item).is_file() for item in HISTORICAL_CONTRACTS):
        errors.append("historical contract missing")

    expected_scope = {
        "syntheticOnly": True,
        "maximumGmailApiMessageRequests": 1,
        "maximumUsersMessagesSendRequests": 1,
        "maximumRecipients": 1,
        "maximumSuccessfulEmailSends": 1,
        "maximumCredentialRefreshRequests": 1,
        "maximumAuthorizationCodeExchanges": 0,
        "maximumOauthSessions": 0,
        "maximumBrowserSessions": 0,
        "maximumSshSessions": 0,
        "maximumTokenExchanges": 0,
        "maximumRetries": 0,
        "maximumFallbacks": 0,
        "maximumAttachments": 0,
        "maximumCc": 0,
        "maximumBcc": 0,
        "maximumBatchOperations": 0,
        "maximumDrafts": 0,
        "maximumMessageReads": 0,
        "maximumMetadataListSearchOperations": 0,
        "maximumGoogleResourceMutations": 0,
        "maximumAccountMutations": 0,
        "maximumDurationMinutes": 15,
        "maximumSpendUsd": 0.1,
        "accountOrResourceMutationAuthorized": False,
        "fallbackAuthorized": False,
    }
    if payload.get("scope") != expected_scope:
        errors.append("bounded scope drifted")

    configuration = payload.get("configuration", {})
    expected_configuration = {
        "providerEnvironmentVariable": "ROUTEMIND_NOTIFICATION_EMAIL_PROVIDER",
        "enabledEnvironmentVariable": "ROUTEMIND_NOTIFICATION_GMAIL_ENABLED",
        "senderEnvironmentVariable": "ROUTEMIND_NOTIFICATION_SENDER",
        "syntheticRecipientEnvironmentVariable": "ROUTEMIND_NOTIFICATION_SYNTHETIC_RECIPIENT",
        "expectedProvider": "gmail",
        "senderBoundary": "EXISTING_APPROVED_SYNTHETIC_CONFIGURATION_ONLY",
        "recipientBoundary": "EXISTING_APPROVED_SYNTHETIC_CONFIGURATION_ONLY",
        "adapterEnabledByDefault": False,
        "manualCredentialFileParsing": False,
    }
    if any(configuration.get(key) != value for key, value in expected_configuration.items()):
        errors.append("configuration boundary drifted")

    data = payload.get("dataBoundary", {})
    if data.get("syntheticOnly") is not True or data.get("rawAddressesInArtifactsLogsEvidenceChat") is not False:
        errors.append("privacy boundary drifted")
    if any("@" in item for item in _strings(payload)):
        errors.append("raw email address present")
    if not {"credential_value", "access_token", "refresh_token", "client_secret", "authorization_header", "raw_token_response", "raw_provider_response", "complete_email_address"}.issubset(set(data.get("forbidden", []))):
        errors.append("credential redaction boundary drifted")

    message = payload.get("message", {})
    if {message.get(key) for key in ("externalUrls", "trackingPixels", "attachments", "cc", "bcc", "businessIdentifiers")} != {0}:
        errors.append("message boundary drifted")

    execution = payload.get("execution", {})
    if {
        execution.get("credentialLoad"), execution.get("readinessCheck"), execution.get("refreshPolicy"),
        execution.get("postRefreshReadiness"), execution.get("sendPolicy"), execution.get("retryPolicy"),
        execution.get("fallbackPolicy"), execution.get("historicalContractReuse"),
        execution.get("oauthBrowserOrSshPath"), execution.get("gmailReads"),
        execution.get("stopAfterAuthorizedRequest"), execution.get("failClosedAfterRefreshOrSendFailure"),
    } != {
        "ONE_EXISTING_CREDENTIAL_OBJECT", "READ_ONLY_NO_NETWORK", "AT_MOST_ONE_ONLY_IF_REQUIRED",
        "REASSESS_SAME_CREDENTIAL_OBJECT", "AT_MOST_ONE_AFTER_USABLE_CREDENTIAL", "ZERO_RETRIES",
        "NO_AUTOMATIC_FALLBACK", "FORBIDDEN", "FORBIDDEN", "FORBIDDEN", True, True,
    }:
        errors.append("execution semantics drifted")

    claims = payload.get("claims", {})
    expected_claims = {
        "contractPrepared": True, "providerValidated": False, "liveCallsExecuted": False,
        "credentialRefreshValidated": False, "sendValidated": False, "deliveryValidated": False,
        "productionValidated": False, "humanGateRequired": True, "historicalContractsPreserved": True,
        "historicalContractsReusable": False, "historicalSesEvidencePreserved": True,
        "round3FrozenSciencePreserved": True,
    }
    if any(claims.get(key) is not expected for key, expected in expected_claims.items()):
        errors.append("claim boundary drifted")

    gate = payload.get("humanGate", {})
    if gate.get("required") is not True or gate.get("approvalAuthorizesOnlyOneRefreshIfRequiredAndOneSyntheticSend") is not True:
        errors.append("human gate boundary drifted")
    return errors


def main() -> int:
    try:
        payload = json.loads(CONTRACT.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: cannot load Gmail refresh-if-required single-send contract: {exc}")
        return 1
    errors = validate(payload)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"PASS: R4-422 Gmail refresh-if-required single-send contract {EXPECTED_DIGEST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
