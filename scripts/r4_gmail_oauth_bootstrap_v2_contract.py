"""Validate the offline-only R4-422 Gmail OAuth bootstrap V2 contract."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/provider/r4-422-google-gmail-oauth-bootstrap-v2.json"
EXPECTED_DIGEST = "e6fc0dec19ea96c2eaee337694e7a0a19716e5491ea4b50d9be09892391ca22e"


def canonical_digest(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def validate(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if canonical_digest(payload) != EXPECTED_DIGEST:
        errors.append("contract digest mismatch")
    identity = {key: payload.get(key) for key in (
        "schemaVersion", "contractId", "taskId", "status", "provider", "operation"
    )}
    if identity != {
        "schemaVersion": 1,
        "contractId": "r4-422-google-gmail-oauth-bootstrap-v2",
        "taskId": "R4-422",
        "status": "PREPARED_GMAIL_OAUTH_BOOTSTRAP_V2_HUMAN_GATE",
        "provider": "GOOGLE_GMAIL_API",
        "operation": "oauth2.installed_app_bootstrap_v2",
    }:
        errors.append("contract identity drifted")
    if payload.get("scope") != "https://www.googleapis.com/auth/gmail.send":
        errors.append("scope drifted")

    configuration = payload.get("configuration", {})
    if {
        configuration.get("clientCredentialEnvironmentVariable"),
        configuration.get("tokenStoreEnvironmentVariable"),
        configuration.get("oauthUserIdEnvironmentVariable"),
        configuration.get("knownHostsEnvironmentVariable"),
        configuration.get("macLoopbackPortEnvironmentVariable"),
    } != {
        "ROUTEMIND_GMAIL_OAUTH_CLIENT_FILE",
        "ROUTEMIND_GMAIL_TOKEN_STORE",
        "ROUTEMIND_GMAIL_OAUTH_USER_ID",
        "ROUTEMIND_GMAIL_OAUTH_MAC_KNOWN_HOSTS",
        "ROUTEMIND_GMAIL_OAUTH_MAC_PORT",
    }:
        errors.append("external configuration boundary drifted")
    if configuration.get("repositoryExternalClientAndTokenStore") is not True:
        errors.append("repository external path boundary drifted")
    if configuration.get("windowsOnlyTokenStore") is not True:
        errors.append("token store host boundary drifted")

    tunnel = payload.get("operatorManagedTunnel", {})
    if tunnel.get("sshAutomation") != 0 or tunnel.get("sshProcessStartedByRouteMind") is not False:
        errors.append("SSH automation boundary drifted")
    if tunnel.get("sshHost") != "10.10.1.27" or tunnel.get("sshUser") != "suzhe":
        errors.append("SSH identity drifted")
    if tunnel.get("operatorEntersPasswordOutsideRouteMind") is not True:
        errors.append("password boundary drifted")
    if tunnel.get("strictHostKeyVerification") is not True or tunnel.get("publicIngress") is not False:
        errors.append("SSH security boundary drifted")
    if tunnel.get("remoteForward") != "127.0.0.1:<mac-port>:127.0.0.1:<windows-port>":
        errors.append("remote forward boundary drifted")

    readiness = payload.get("readinessGate", {})
    if readiness.get("preflightPath") != "/routemind-oauth-preflight":
        errors.append("preflight path drifted")
    if readiness.get("preflightResponse") != "ROUTEMIND_GMAIL_OAUTH_TUNNEL_READY":
        errors.append("preflight response drifted")
    if readiness.get("requiredValidPreflightRequests") != 1:
        errors.append("preflight request bound drifted")
    if readiness.get("authorizationUrlBeforePreflight") is not False:
        errors.append("authorization URL readiness gate drifted")
    if readiness.get("preflightConsumesOAuthState") is not False:
        errors.append("preflight state boundary drifted")

    authorization = payload.get("authorization", {})
    if {
        authorization.get("interactiveSessions"),
        authorization.get("callbackConsumptions"),
        authorization.get("tokenExchange"),
    } != {1}:
        errors.append("OAuth execution bound drifted")
    if authorization.get("callbackPath") != "/oauth2callback" or authorization.get("stateMustMatch") is not True:
        errors.append("callback boundary drifted")

    execution = payload.get("execution", {})
    if execution.get("maximumGoogleApiMessageRequests") != 0 or execution.get("maximumEmailSends") != 0:
        errors.append("message operation boundary drifted")
    if execution.get("maximumRetries") != 0 or execution.get("maximumFallback") != 0:
        errors.append("retry/fallback boundary drifted")
    if execution.get("maximumDurationMinutes") != 15 or execution.get("maximumSpendUsd") != 0.1:
        errors.append("time/cost boundary drifted")
    if execution.get("googleResourceMutations") != 0 or execution.get("accountMutations") != 0:
        errors.append("mutation boundary drifted")

    failure = payload.get("failureSemantics", {})
    if any(failure.get(key) is not True for key in (
        "failClosed", "noAuthorizationUrlBeforeTunnelPreflightPass", "zeroSecondSession",
        "zeroRetryAfterFailure", "zeroCodePersistence", "zeroTokenLogging",
        "duplicateCallbackRejected", "timeoutTeardownRequired"
    )):
        errors.append("fail-closed semantics drifted")

    forbidden = set(payload.get("forbiddenOperations", []))
    required_forbidden = {
        "automatic_ssh_launch", "ssh_password_capture_or_automation",
        "oauth_authorization_before_preflight", "users.messages.send",
        "broader_OAuth_scopes", "credential_disclosure", "automatic_retry",
        "automatic_fallback",
    }
    if not required_forbidden.issubset(forbidden):
        errors.append("forbidden operation boundary drifted")

    claims = payload.get("claims", {})
    if any(claims.get(key) is not False for key in (
        "oauthExecuted", "tokenExchangeExecuted", "gmailMessageOperationExecuted",
        "emailSent", "productionValidated"
    )) or claims.get("humanGateRequired") is not True:
        errors.append("execution claims drifted")
    return errors


def main() -> int:
    try:
        payload = json.loads(CONTRACT.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: cannot load Gmail OAuth bootstrap V2 contract: {exc}")
        return 1
    errors = validate(payload)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"PASS: R4-422 Gmail OAuth bootstrap V2 contract {EXPECTED_DIGEST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
