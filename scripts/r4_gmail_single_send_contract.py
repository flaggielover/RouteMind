"""Validate the offline-only R4-422 exactly-one Gmail send contract."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/provider/r4-422-google-gmail-single-send-validation-v1.json"
EXPECTED_DIGEST = "16e6f9dd68fd261f28047b0e7ea8e2f19e186ba3c04dd68c7c8a7d3606dea663"


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
        "contractId": "r4-422-google-gmail-single-send-validation-v1",
        "taskId": "R4-422",
        "status": "PREPARED_GOOGLE_GMAIL_SINGLE_SEND_HUMAN_GATE",
        "provider": "GOOGLE_GMAIL",
        "api": "Gmail API v1",
        "operation": "users.messages.send",
        "channel": "EMAIL",
    }:
        errors.append("contract identity drifted")

    auth = payload.get("authentication", {})
    if {
        auth.get("scope"), auth.get("credentialSource"), auth.get("oauthSessionsAuthorized"),
        auth.get("tokenExchangesAuthorized"), auth.get("browserLoginAuthorized"), auth.get("sshAuthorized")
    } != {
        "https://www.googleapis.com/auth/gmail.send", "EXTERNAL_WINDOWS_OAUTH_TOKEN_STORE", 0, 0, False, False
    }:
        errors.append("authentication boundary drifted")

    expected_scope = {
        "syntheticOnly": True,
        "maximumGmailApiMessageRequests": 1,
        "maximumUsersMessagesSendRequests": 1,
        "maximumRecipients": 1,
        "maximumSuccessfulEmailSends": 1,
        "maximumRetries": 0,
        "maximumFallbacks": 0,
        "maximumAttachments": 0,
        "maximumCc": 0,
        "maximumBcc": 0,
        "maximumBatchOperations": 0,
        "maximumDrafts": 0,
        "maximumMessageReads": 0,
        "maximumMetadataListSearchOperations": 0,
        "maximumOauthSessions": 0,
        "maximumTokenExchanges": 0,
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
    expected_env = {
        "providerEnvironmentVariable": "ROUTEMIND_NOTIFICATION_EMAIL_PROVIDER",
        "enabledEnvironmentVariable": "ROUTEMIND_NOTIFICATION_GMAIL_ENABLED",
        "senderEnvironmentVariable": "ROUTEMIND_NOTIFICATION_SENDER",
        "syntheticRecipientEnvironmentVariable": "ROUTEMIND_NOTIFICATION_SYNTHETIC_RECIPIENT",
        "expectedProvider": "gmail",
        "adapterEnabledByDefault": False,
    }
    if any(configuration.get(key) != value for key, value in expected_env.items()):
        errors.append("configuration boundary drifted")
    if configuration.get("senderBoundary") != "EXISTING_APPROVED_SYNTHETIC_CONFIGURATION_ONLY" or configuration.get("recipientBoundary") != "EXISTING_APPROVED_SYNTHETIC_CONFIGURATION_ONLY":
        errors.append("endpoint boundary drifted")

    data = payload.get("dataBoundary", {})
    if data.get("syntheticOnly") is not True or data.get("rawAddressesInArtifactsLogsOrChat") is not False:
        errors.append("privacy boundary drifted")
    if any("@" in item for item in _strings(payload)):
        errors.append("raw email address present")
    forbidden = set(data.get("forbidden", []))
    if not {"credential_value", "access_token", "refresh_token", "client_secret"}.issubset(forbidden):
        errors.append("credential redaction boundary drifted")

    execution = payload.get("execution", {})
    if {
        execution.get("retryPolicy"), execution.get("fallbackPolicy"), execution.get("historicalSesPath"),
        execution.get("secondSend"), execution.get("stopAfterAuthorizedRequest")
    } != {"ZERO_RETRIES", "NO_AUTOMATIC_FALLBACK", "FORBIDDEN", "REJECTED_LOCALLY", True}:
        errors.append("execution semantics drifted")

    claims = payload.get("claims", {})
    if any(claims.get(key) is not expected for key, expected in {
        "contractPrepared": True, "providerValidated": False, "liveCallsExecuted": False,
        "deliveryValidated": False, "productionValidated": False, "humanGateRequired": True,
        "historicalSesEvidencePreserved": True, "round3FrozenSciencePreserved": True,
    }.items()):
        errors.append("claim boundary drifted")

    gate = payload.get("humanGate", {})
    if gate.get("required") is not True or gate.get("approvalAuthorizesOnlyOneSyntheticSend") is not True:
        errors.append("human gate boundary drifted")
    return errors


def main() -> int:
    try:
        payload = json.loads(CONTRACT.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: cannot load Gmail single-send contract: {exc}")
        return 1
    errors = validate(payload)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"PASS: R4-422 Gmail exactly-one send contract {EXPECTED_DIGEST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
