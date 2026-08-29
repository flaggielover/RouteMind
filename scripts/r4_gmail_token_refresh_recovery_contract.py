"""Validate the offline-only R4-422 Gmail credential refresh contract."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/provider/r4-422-google-gmail-token-refresh-recovery-v1.json"
EXPECTED_DIGEST = "6c2b454101787c72459b3a5a7f01c18b25cf09d19ffd8ed90aaf3044e8b4b39f"


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
    identity = {key: payload.get(key) for key in ("schemaVersion", "contractId", "taskId", "status", "provider", "purpose")}
    if identity != {
        "schemaVersion": 1,
        "contractId": "r4-422-google-gmail-token-refresh-recovery-v1",
        "taskId": "R4-422",
        "status": "PREPARED_GOOGLE_GMAIL_TOKEN_REFRESH_RECOVERY_HUMAN_GATE",
        "provider": "GOOGLE_OAUTH",
        "purpose": "GMAIL_CREDENTIAL_REFRESH_ONLY",
    }:
        errors.append("contract identity drifted")

    auth = payload.get("authentication", {})
    if {
        auth.get("scope"), auth.get("credentialSource"), auth.get("tokenStoreEnvironmentVariable"),
        auth.get("expectedOauthUserId"),
    } != {
        "https://www.googleapis.com/auth/gmail.send", "EXTERNAL_WINDOWS_OAUTH_TOKEN_STORE",
        "ROUTEMIND_GMAIL_TOKEN_STORE", "default",
    }:
        errors.append("authentication boundary drifted")

    expected_scope = {
        "maximumTokenRefreshRequests": 1,
        "maximumAuthorizationCodeExchanges": 0,
        "maximumOauthAuthorizationSessions": 0,
        "maximumBrowserSessions": 0,
        "maximumSshSessions": 0,
        "maximumGmailApiRequests": 0,
        "maximumUsersMessagesSendRequests": 0,
        "maximumEmailSends": 0,
        "maximumRetries": 0,
        "maximumFallbacks": 0,
        "maximumGoogleResourceMutations": 0,
        "maximumAccountMutations": 0,
        "maximumDurationMinutes": 10,
        "maximumSpendUsd": 0.1,
        "productionClaim": "forbidden",
    }
    if payload.get("scope") != expected_scope:
        errors.append("bounded scope drifted")

    configuration = payload.get("configuration", {})
    if configuration.get("adapterEnabledByDefault") is not False or configuration.get("gmailMessageOperations") != "forbidden":
        errors.append("configuration boundary drifted")
    if configuration.get("manualCredentialFileParsing") is not False:
        errors.append("manual credential parsing boundary drifted")

    data = payload.get("dataBoundary", {})
    if data.get("credentialValues") != "forbidden" or data.get("rawTokenResponses") != "forbidden":
        errors.append("credential redaction boundary drifted")
    if any("@" in item for item in _strings(payload)):
        errors.append("raw email address present")

    execution = payload.get("execution", {})
    if {
        execution.get("requestCount"), execution.get("retryPolicy"), execution.get("fallbackPolicy"),
        execution.get("stopImmediatelyAfterRefresh"),
    } != {"at_most_one", "ZERO_RETRIES", "NO_FALLBACK", True}:
        errors.append("execution semantics drifted")

    claims = payload.get("claims", {})
    if any(claims.get(key) is not expected for key, expected in {
        "contractPrepared": True, "credentialRefreshValidated": False, "gmailConnectivityValidated": False,
        "gmailMessageOperationValidated": False, "emailDeliveryValidated": False, "productionValidated": False,
        "humanGateRequired": True, "historicalContractsPreserved": True, "round3FrozenSciencePreserved": True,
    }.items()):
        errors.append("claim boundary drifted")

    gate = payload.get("humanGate", {})
    if gate.get("required") is not True or gate.get("approvalAuthorizesOnlyOneExistingCredentialRefresh") is not True:
        errors.append("human gate boundary drifted")
    return errors


def main() -> int:
    try:
        payload = json.loads(CONTRACT.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: cannot load Gmail refresh contract: {exc}")
        return 1
    errors = validate(payload)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"PASS: R4-422 Gmail refresh-only contract {EXPECTED_DIGEST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
