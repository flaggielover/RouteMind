"""Validate the offline-only R4-422 Gmail live contract."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/provider/r4-422-google-gmail-live-validation-v1.json"
EXPECTED_DIGEST = "bc05c17490bcf1be3bd444ead6a68e941b29b0a09d71842283b228f8c5a811f1"


def canonical_digest(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def validate(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if canonical_digest(payload) != EXPECTED_DIGEST:
        errors.append("contract digest mismatch")
    if {
        "schemaVersion": payload.get("schemaVersion"),
        "contractId": payload.get("contractId"),
        "taskId": payload.get("taskId"),
        "status": payload.get("status"),
        "provider": payload.get("provider"),
        "operation": payload.get("operation"),
    } != {
        "schemaVersion": 1,
        "contractId": "r4-422-google-gmail-live-validation-v1",
        "taskId": "R4-422",
        "status": "PREPARED_GOOGLE_GMAIL_LIVE_EXECUTION_HUMAN_GATE",
        "provider": "GOOGLE_GMAIL_API",
        "operation": "users.messages.send",
    }:
        errors.append("contract identity drifted")
    auth = payload.get("authentication", {})
    if auth.get("scope") != "https://www.googleapis.com/auth/gmail.send" or auth.get("interactiveConsentAtStartup") is not False:
        errors.append("oauth scope/startup semantics drifted")
    scope = payload.get("scope", {})
    expected_scope = {
        "syntheticOnly": True,
        "maximumSendRequests": 1,
        "maximumRecipients": 1,
        "maximumCc": 0,
        "maximumBcc": 0,
        "maximumAttachments": 0,
        "maximumBulkOperations": 0,
        "maximumRetries": 0,
        "maximumDurationMinutes": 15,
        "maximumSpendUsd": 0.1,
        "accountOrResourceMutationAuthorized": False,
        "oauthConsentAuthorized": False,
        "fallbackAuthorized": False,
    }
    if scope != expected_scope:
        errors.append("bounded scope drifted")
    data = payload.get("dataBoundary", {})
    if "credential_value" not in data.get("forbidden", []) or "synthetic_sender" not in data.get("allowed", []):
        errors.append("data boundary drifted")
    execution = payload.get("execution", {})
    if execution.get("retryPolicy") != "ZERO_RETRIES" or execution.get("fallbackPolicy") != "NO_AUTOMATIC_FALLBACK":
        errors.append("retry/fallback semantics drifted")
    claims = payload.get("claims", {})
    if claims.get("liveCallsExecuted") is not False or claims.get("providerValidated") is not False or claims.get("humanGateRequired") is not True:
        errors.append("claim boundary drifted")
    return errors


def main() -> int:
    try:
        payload = json.loads(CONTRACT.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: cannot load Gmail contract: {exc}")
        return 1
    errors = validate(payload)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"PASS: R4-422 Gmail contract {EXPECTED_DIGEST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
