from __future__ import annotations

import argparse
import os
import socket
import subprocess
import time
from dataclasses import replace
from pathlib import Path
from typing import Any

from r4_ssh_readiness import (
    Observation,
    SshReadinessError,
    atomic_write_json,
    build_artifact,
    persist_target_artifact,
    strict_loads,
    utc_now,
)

MAX_BANNER_BYTES = 255


def _safe_banner(value: bytes) -> str:
    return "".join(chr(byte) if 32 <= byte <= 126 else "?" for byte in value[:MAX_BANNER_BYTES])


def probe_tcp_banner(host: str, *, timeout_seconds: float = 10.0) -> dict[str, Any]:
    observed_at = utc_now()
    try:
        resolved = socket.gethostbyname(host)
        with socket.create_connection((resolved, 22), timeout=timeout_seconds) as connection:
            connection.settimeout(timeout_seconds)
            try:
                raw_banner = connection.recv(MAX_BANNER_BYTES)
            except socket.timeout:
                raw_banner = b""
            banner = _safe_banner(raw_banner)
            return {
                "observedAt": observed_at,
                "resolvedIp": resolved,
                "tcp": "OK",
                "banner": "VALID" if banner.startswith("SSH-2.0-") else ("MISSING" if not banner else "MALFORMED"),
                "serverBanner": banner,
            }
    except TimeoutError:
        return {"observedAt": observed_at, "tcp": "TIMEOUT", "banner": "MISSING"}
    except ConnectionResetError:
        return {"observedAt": observed_at, "tcp": "RESET", "banner": "MISSING"}
    except OSError as exc:
        return {
            "observedAt": observed_at,
            "tcp": "ERROR",
            "banner": "MISSING",
            "errorType": exc.__class__.__name__,
        }


def known_hosts_has_fingerprint(path: Path, expected: str, host: str) -> bool:
    if not path.is_file() or not expected.startswith("SHA256:"):
        return False
    matched = subprocess.run(
        ["ssh-keygen", "-F", host, "-f", str(path)],
        capture_output=True,
        text=True,
        check=False,
    )
    if matched.returncode != 0 or not matched.stdout.strip():
        return False
    result = subprocess.run(
        ["ssh-keygen", "-lf", "-", "-E", "sha256"],
        input=matched.stdout,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0 and any(
        len(line.split()) >= 2 and line.split()[1] == expected
        for line in result.stdout.splitlines()
    )


def pin_known_host(
    *, host: str, expected_host_key_sha256: str, destination: Path, timeout_seconds: int
) -> bool:
    scan = subprocess.run(
        ["ssh-keyscan", "-T", str(timeout_seconds), "-t", "ed25519", host],
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout_seconds + 5,
    )
    public_lines = [
        line
        for line in scan.stdout.splitlines()
        if line and not line.startswith("#") and " ssh-ed25519 " in line
    ]
    if scan.returncode != 0 or not public_lines:
        return False
    fingerprints = subprocess.run(
        ["ssh-keygen", "-lf", "-", "-E", "sha256"],
        input="\n".join(public_lines) + "\n",
        capture_output=True,
        text=True,
        check=False,
    )
    if fingerprints.returncode != 0 or not any(
        len(line.split()) >= 2 and line.split()[1] == expected_host_key_sha256
        for line in fingerprints.stdout.splitlines()
    ):
        return False
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + ".tmp")
    temporary.write_text("\n".join(public_lines) + "\n", encoding="utf-8", newline="\n")
    os.replace(temporary, destination)
    return known_hosts_has_fingerprint(destination, expected_host_key_sha256, host)


def run_strict_ssh(
    *,
    host: str,
    username: str,
    private_key: Path,
    known_hosts: Path,
    expected_host_key_sha256: str,
    timeout_seconds: int,
) -> tuple[Observation, dict[str, Any], dict[str, Any] | None]:
    pinned_fingerprint = known_hosts_has_fingerprint(
        known_hosts, expected_host_key_sha256, host
    )
    command = [
        "ssh",
        "-vv",
        "-i",
        str(private_key),
        "-o",
        "BatchMode=yes",
        "-o",
        "StrictHostKeyChecking=yes",
        "-o",
        f"UserKnownHostsFile={known_hosts}",
        "-o",
        f"ConnectTimeout={timeout_seconds}",
        "-o",
        "NumberOfPasswordPrompts=0",
        f"{username}@{host}",
        "cat /var/lib/routemind-ssh-readiness/guest-readiness.json",
    ]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout_seconds + 10,
        )
    except subprocess.TimeoutExpired:
        observation = replace(
            Observation(),
            kex_started=False,
            host_key="ABSENT",
            auth_started=False,
            auth="NOT_STARTED",
            cloud_init="NOT_OBSERVED",
            bootstrap_ready=False,
        )
        return observation, {"ssh": "TIMEOUT", "authStarted": False}, None
    debug = result.stderr
    host_changed = "REMOTE HOST IDENTIFICATION HAS CHANGED" in debug
    host_verified = "is known and matches" in debug
    kex_started = "kex: algorithm:" in debug or "SSH2_MSG_KEXINIT" in debug
    auth_started = pinned_fingerprint and (
        "Offering public key" in debug
        or "Authentications that can continue" in debug
        or result.returncode == 0
    )
    host_key_status = (
        "CHANGED"
        if host_changed
        else "VERIFIED"
        if pinned_fingerprint and host_verified
        else "ABSENT"
        if not pinned_fingerprint
        else "MISMATCH"
    )
    observation = Observation(
        kex_started=kex_started,
        host_key=host_key_status,
        auth_started=auth_started,
        auth="AUTHENTICATED" if result.returncode == 0 else "REJECTED",
        cloud_init="NOT_OBSERVED",
        bootstrap_ready=False,
    )
    guest: dict[str, Any] | None = None
    if result.returncode == 0 and host_key_status == "VERIFIED":
        try:
            candidate = strict_loads(result.stdout)
            if not isinstance(candidate, dict) or candidate.get("schema") != "r4-vm-ssh-readiness-guest-artifact.v1":
                raise SshReadinessError("guest artifact schema")
            guest = candidate
            cloud_complete = str(candidate.get("cloudInitStatus", "")).strip().lower().endswith("done")
            bootstrap_ready = all(
                candidate.get(field) is True
                for field in (
                    "authorizedKeyFingerprintMatch",
                    "sshListenerPresent",
                    "sshdConfigValid",
                    "sshServiceActive",
                )
            )
            observation = replace(
                observation,
                cloud_init="COMPLETE" if cloud_complete else "INCOMPLETE",
                bootstrap_ready=bootstrap_ready,
            )
        except SshReadinessError:
            observation = replace(observation, cloud_init="INCOMPLETE", bootstrap_ready=False)
    semantic_raw = {
        "sshExitCode": result.returncode,
        "kexStarted": kex_started,
        "hostKeyChanged": host_changed,
        "hostKeyVerifiedAgainstPinnedFingerprint": host_key_status == "VERIFIED",
        "authStarted": auth_started,
        "guestArtifactPresent": guest is not None,
    }
    return observation, semantic_raw, guest


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a bounded, non-mutating SSH-readiness probe")
    parser.add_argument("--execution-id", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--host", required=True)
    parser.add_argument("--artifact-root", required=True, type=Path)
    parser.add_argument("--known-hosts", required=True, type=Path)
    parser.add_argument("--expected-host-key-sha256", default="")
    parser.add_argument("--username", default="root", choices=("root",))
    parser.add_argument("--maximum-minutes", type=int, default=60, choices=range(1, 61))
    arguments = parser.parse_args()
    key_value = os.environ.get("ROUTEMIND_SSH_PRIVATE_KEY_PATH", "")
    private_key = Path(key_value)
    if not private_key.is_file():
        raise SystemExit("configured SSH private-key file is unavailable")

    deadline = time.monotonic() + arguments.maximum_minutes * 60
    attempts: list[dict[str, Any]] = []
    observation = replace(
        Observation(),
        tcp="ERROR",
        banner="MISSING",
        kex_started=False,
        host_key="ABSENT",
        auth_started=False,
        auth="NOT_STARTED",
        cloud_init="NOT_OBSERVED",
        bootstrap_ready=False,
    )
    backoff = (0, 5, 10, 15, 30, 60)
    guest_artifact: dict[str, Any] | None = None
    for retry, delay in enumerate(backoff):
        if time.monotonic() >= deadline:
            break
        if delay:
            time.sleep(min(delay, max(0, deadline - time.monotonic())))
        network = probe_tcp_banner(arguments.host)
        attempt: dict[str, Any] = {"attempt": retry + 1, "backoffSeconds": delay, **network}
        observation = replace(
            observation,
            tcp=str(network["tcp"]),
            banner=str(network["banner"]),
            kex_started=False,
        )
        if network["tcp"] == "OK" and network["banner"] == "VALID":
            out_of_band_key_available = bool(arguments.expected_host_key_sha256)
            attempt["outOfBandHostKeyAvailable"] = out_of_band_key_available
            if out_of_band_key_available and not known_hosts_has_fingerprint(
                arguments.known_hosts, arguments.expected_host_key_sha256, arguments.host
            ):
                try:
                    pinned = pin_known_host(
                        host=arguments.host,
                        expected_host_key_sha256=arguments.expected_host_key_sha256,
                        destination=arguments.known_hosts,
                        timeout_seconds=10,
                    )
                except (OSError, subprocess.TimeoutExpired):
                    pinned = False
                attempt["hostKeyPinnedFromOutOfBandFingerprint"] = pinned
            ssh_observation, semantic_raw, guest_artifact = run_strict_ssh(
                host=arguments.host,
                username=arguments.username,
                private_key=private_key,
                known_hosts=arguments.known_hosts,
                expected_host_key_sha256=(
                    arguments.expected_host_key_sha256
                    if out_of_band_key_available
                    else "OUT_OF_BAND_HOST_KEY_UNAVAILABLE"
                ),
                timeout_seconds=10,
            )
            observation = ssh_observation
            attempt.update(semantic_raw)
        attempts.append(attempt)
        artifact = build_artifact(
            execution_id=arguments.execution_id,
            target=arguments.target,
            observation=observation,
            attempts=attempts,
        )
        persist_target_artifact(arguments.artifact_root, artifact)
        if artifact["terminalClassification"] == "READY":
            break
    if guest_artifact is not None:
        guest_path = arguments.artifact_root / "raw" / f"{arguments.target}-guest-readiness.json"
        atomic_write_json(guest_path, guest_artifact)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
