"""Validate the password-authenticated synthetic remote-forward contract."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/provider/r4-422-google-gmail-oauth-password-remote-forward-v1.json"
EXPECTED_DIGEST = "3c8cb8104cad351b74620f68fa02129c516a46a458401ae78a909b3879aec215"


def canonical_digest(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def validate(payload: dict[str, Any], expected_digest: str | None = None) -> list[str]:
    errors: list[str] = []
    if expected_digest and canonical_digest(payload) != expected_digest:
        errors.append("contract digest mismatch")
    if payload.get("contractId") != "r4-422-google-gmail-oauth-password-remote-forward-v1":
        errors.append("contract identity drifted")
    if payload.get("taskId") != "R4-422":
        errors.append("task identity drifted")
    if payload.get("status") != "PREPARED_PASSWORD_REMOTE_FORWARD_SYNTHETIC_HUMAN_GATE":
        errors.append("contract must remain Human Gate pending")
    if payload.get("provider") != "GOOGLE_GMAIL_API" or payload.get("scope") != "https://www.googleapis.com/auth/gmail.send":
        errors.append("provider or scope drifted")
    configuration = payload.get("configuration", {})
    if configuration.get("passwordEnvironmentVariable") != "FORBIDDEN" or configuration.get("passwordStore") != "FORBIDDEN":
        errors.append("password secret boundary drifted")
    topology = payload.get("crossDeviceTopology", {})
    if topology.get("sshHost") != "10.10.1.27" or topology.get("sshUser") != "suzhe":
        errors.append("fixed Mac SSH identity drifted")
    if topology.get("remoteForward") != "127.0.0.1:<mac-port>:127.0.0.1:<windows-port>":
        errors.append("remote forward drifted")
    if topology.get("remoteBind") != "MAC_LOOPBACK_ONLY" or topology.get("windowsDestination") != "WINDOWS_LOOPBACK_ONLY":
        errors.append("loopback boundary drifted")
    if topology.get("publicIngress") is not False:
        errors.append("public ingress must remain disabled")
    password = payload.get("passwordBoundary", {})
    if (
        password.get("operatorTypesInWindowsTerminal") is not True
        or password.get("codexReadsPassword") is not False
        or password.get("codexCapturesPassword") is not False
        or password.get("codexLogsPassword") is not False
        or password.get("codexPersistsPassword") is not False
        or password.get("passwordAutomation") is not False
        or password.get("pubkeyAuthentication") is not False
        or password.get("batchMode") is not False
        or password.get("maxPasswordPrompts") != 1
    ):
        errors.append("interactive password boundary drifted")
    synthetic = payload.get("syntheticValidation", {})
    if (
        synthetic.get("authorized") is not True
        or synthetic.get("requestCount") != 1
        or synthetic.get("googleRequests") != 0
        or synthetic.get("oauthSessions") != 0
        or synthetic.get("tokenExchanges") != 0
        or synthetic.get("gmailMessageRequests") != 0
        or synthetic.get("emailSends") != 0
    ):
        errors.append("synthetic-only execution boundary drifted")
    execution = payload.get("execution", {})
    if execution.get("maximumSshConnections") != 1 or execution.get("maximumRemoteForwards") != 1 or execution.get("maximumSyntheticRequests") != 1:
        errors.append("execution limits drifted")
    if execution.get("automaticRetry") is not False or execution.get("automaticFallback") is not False:
        errors.append("retry/fallback boundary drifted")
    claims = payload.get("claims", {})
    for key in ("syntheticProbeExecuted", "sshTunnelExecuted", "oauthExecuted", "tokenExchangeExecuted", "emailSent"):
        if claims.get(key) is not False:
            errors.append("execution claim drifted")
    if claims.get("humanGateRequired") is not True:
        errors.append("Human Gate boundary drifted")
    forbidden = set(payload.get("forbiddenOperations", []))
    required_forbidden = {
        "IdentityFile",
        "IdentitiesOnly",
        "BatchMode=yes",
        "sshpass",
        "expect",
        "password_automation",
        "OAuth_authorization",
        "token_exchange",
        "users.messages.send",
    }
    if required_forbidden - forbidden:
        errors.append("forbidden operation boundary drifted")
    return errors


def main() -> int:
    try:
        payload = json.loads(CONTRACT.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: cannot load password remote-forward contract: {exc}")
        return 1
    errors = validate(payload, EXPECTED_DIGEST)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"PASS: R4-422 password remote-forward contract {EXPECTED_DIGEST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
