"""Validate the offline-only cross-device Gmail OAuth bootstrap contract."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/provider/r4-422-google-gmail-oauth-remote-forward-bootstrap-v1.json"


def canonical_digest(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def validate(payload: dict[str, Any], expected_digest: str | None = None) -> list[str]:
    errors: list[str] = []
    if expected_digest and canonical_digest(payload) != expected_digest:
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
        "contractId": "r4-422-google-gmail-oauth-remote-forward-bootstrap-v1",
        "taskId": "R4-422",
        "status": "PREPARED_GMAIL_OAUTH_CROSS_DEVICE_BOOTSTRAP_HUMAN_GATE",
        "provider": "GOOGLE_GMAIL_API",
        "operation": "oauth2.installed_app_bootstrap",
    }:
        errors.append("contract identity drifted")
    if payload.get("scope") != "https://www.googleapis.com/auth/gmail.send":
        errors.append("scope drifted")
    configuration = payload.get("configuration", {})
    required_configuration = {
        "ROUTEMIND_GMAIL_OAUTH_CLIENT_FILE",
        "ROUTEMIND_GMAIL_TOKEN_STORE",
        "ROUTEMIND_GMAIL_OAUTH_USER_ID",
        "ROUTEMIND_REPOSITORY_ROOT",
        "ROUTEMIND_GMAIL_OAUTH_MAC_SSH_KEY_PATH",
        "ROUTEMIND_GMAIL_OAUTH_MAC_KNOWN_HOSTS",
        "ROUTEMIND_GMAIL_OAUTH_MAC_PORT",
    }
    configured = {
        configuration.get("clientCredentialEnvironmentVariable"),
        configuration.get("tokenStoreEnvironmentVariable"),
        configuration.get("oauthUserIdEnvironmentVariable"),
        configuration.get("repositoryRootEnvironmentVariable"),
        configuration.get("sshIdentityEnvironmentVariable"),
        configuration.get("knownHostsEnvironmentVariable"),
        configuration.get("macLoopbackPortEnvironmentVariable"),
    }
    if configured != required_configuration:
        errors.append("external configuration boundary drifted")
    topology = payload.get("crossDeviceTopology", {})
    if topology.get("sshHost") != "10.10.1.27" or topology.get("sshUser") != "suzhe":
        errors.append("fixed Mac SSH identity drifted")
    if topology.get("remoteForward") != "127.0.0.1:<mac-port>:127.0.0.1:<windows-port>":
        errors.append("remote forward boundary drifted")
    if topology.get("remoteBind") != "MAC_LOOPBACK_ONLY" or topology.get("windowsDestination") != "WINDOWS_LOOPBACK_ONLY":
        errors.append("loopback boundary drifted")
    if topology.get("publicIngress") is not False:
        errors.append("public ingress must remain disabled")
    authorization = payload.get("authorization", {})
    if authorization.get("interactiveSessions") != 1 or authorization.get("tokenExchangeOnWindows") != 1:
        errors.append("OAuth execution bound drifted")
    execution = payload.get("execution", {})
    if (
        execution.get("maximumSshConnections") != 1
        or execution.get("maximumRemoteForwards") != 1
        or execution.get("maximumGoogleOAuthAuthorizationSessions") != 1
        or execution.get("maximumTokenExchanges") != 1
        or execution.get("maximumGoogleApiMessageRequests") != 0
        or execution.get("maximumEmailSends") != 0
        or execution.get("remoteCommands") != 0
        or execution.get("googleCloudMutations") != 0
    ):
        errors.append("execution limits drifted")
    if execution.get("automaticRetry") is not False or execution.get("automaticFallback") is not False:
        errors.append("retry/fallback boundary drifted")
    claims = payload.get("claims", {})
    if any(claims.get(key) is not False for key in ("sshTunnelExecuted", "oauthExecuted", "tokenExchangeExecuted", "emailSent")):
        errors.append("execution claims drifted")
    if claims.get("humanGateRequired") is not True:
        errors.append("Human Gate boundary drifted")
    forbidden = set(payload.get("forbiddenOperations", []))
    required_forbidden = {
        "users.messages.send",
        "broader_OAuth_scopes",
        "credential_disclosure",
        "wildcard_remote_forward_bind",
        "GatewayPorts",
        "remote_shell_or_command_execution",
        "Mac_token_store_persistence",
    }
    if required_forbidden - forbidden:
        errors.append("forbidden operation boundary drifted")
    return errors


def main() -> int:
    try:
        payload = json.loads(CONTRACT.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: cannot load Gmail remote-forward contract: {exc}")
        return 1
    expected = "2ef914d10c541f800a61107bc521f3edbfcec05b608b8dc52c6c65bcd102c629"
    errors = validate(payload, expected)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"PASS: R4-422 Gmail OAuth remote-forward contract {expected}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
