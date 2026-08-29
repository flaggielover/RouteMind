"""Validate the offline-only R4-422 Gmail OAuth bootstrap contract."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/provider/r4-422-google-gmail-oauth-bootstrap-v1.json"
EXPECTED_DIGEST = "ca3c1974b846f83846724091416f41bc431d51d9e26f1bfcdaac2b05c0ab9284"


def canonical_digest(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def validate(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if canonical_digest(payload) != EXPECTED_DIGEST:
        errors.append("contract digest mismatch")
    identity = {
        "schemaVersion": payload.get("schemaVersion"),
        "contractId": payload.get("contractId"),
        "taskId": payload.get("taskId"),
        "status": payload.get("status"),
        "provider": payload.get("provider"),
        "operation": payload.get("operation"),
    }
    if identity != {
        "schemaVersion": 1,
        "contractId": "r4-422-google-gmail-oauth-bootstrap-v1",
        "taskId": "R4-422",
        "status": "PREPARED_GMAIL_OAUTH_BOOTSTRAP_HUMAN_GATE",
        "provider": "GOOGLE_GMAIL_API",
        "operation": "oauth2.installed_app_bootstrap",
    }:
        errors.append("contract identity drifted")
    if payload.get("scope") != "https://www.googleapis.com/auth/gmail.send":
        errors.append("scope drifted")
    configuration = payload.get("configuration", {})
    if {
        configuration.get("clientCredentialEnvironmentVariable"),
        configuration.get("tokenStoreEnvironmentVariable"),
        configuration.get("oauthUserIdEnvironmentVariable"),
    } != {
        "ROUTEMIND_GMAIL_OAUTH_CLIENT_FILE",
        "ROUTEMIND_GMAIL_TOKEN_STORE",
        "ROUTEMIND_GMAIL_OAUTH_USER_ID",
    }:
        errors.append("external configuration boundary drifted")
    authorization = payload.get("authorization", {})
    if authorization.get("interactiveSessions") != 1 or authorization.get("tokenExchange") != 1:
        errors.append("OAuth execution bound drifted")
    if authorization.get("operatorMustPerformLoginAndConsent") is not True:
        errors.append("operator consent boundary drifted")
    execution = payload.get("execution", {})
    if execution.get("maximumGoogleApiMessageRequests") != 0 or execution.get("maximumEmailSends") != 0:
        errors.append("message operation boundary drifted")
    if execution.get("automaticRetry") is not False or execution.get("automaticFallback") is not False:
        errors.append("retry/fallback boundary drifted")
    claims = payload.get("claims", {})
    if claims.get("oauthExecuted") is not False or claims.get("tokenExchangeExecuted") is not False:
        errors.append("execution claims drifted")
    if claims.get("humanGateRequired") is not True:
        errors.append("Human Gate boundary drifted")
    forbidden = set(payload.get("forbiddenOperations", []))
    if {"users.messages.send", "broader_OAuth_scopes", "credential_disclosure"} - forbidden:
        errors.append("forbidden operation boundary drifted")
    return errors


def main() -> int:
    try:
        payload = json.loads(CONTRACT.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: cannot load Gmail OAuth bootstrap contract: {exc}")
        return 1
    errors = validate(payload)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"PASS: R4-422 Gmail OAuth bootstrap contract {EXPECTED_DIGEST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
