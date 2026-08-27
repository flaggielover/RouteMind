from __future__ import annotations

import argparse
import json
import os
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = "r4-vm-ssh-readiness-artifact.v1"
STAGES = (
    "VM_CREATED",
    "PUBLIC_IP_ASSIGNED",
    "TCP22_REACHABLE",
    "SSH_BANNER_RECEIVED",
    "SSH_KEX_STARTED",
    "SSH_HOST_KEY_VERIFIED",
    "SSH_AUTH_STARTED",
    "SSH_AUTHENTICATED",
    "CLOUD_INIT_COMPLETE",
    "ROUTEMIND_BOOTSTRAP_READY",
)
STAGE_STATUSES = {"PASS", "FAIL", "NOT_REACHED"}
TERMINAL_CLASSIFICATIONS = {
    "READY",
    "VM_NOT_CREATED",
    "PUBLIC_IP_MISSING",
    "TCP_TIMEOUT",
    "TCP_RESET",
    "TCP_ERROR",
    "SSH_BANNER_NOT_RECEIVED",
    "SSH_BANNER_MALFORMED",
    "SSH_KEX_TIMEOUT",
    "SSH_HOST_KEY_ABSENT",
    "SSH_HOST_KEY_CHANGED",
    "SSH_HOST_KEY_MISMATCH",
    "SSH_AUTH_REJECTED",
    "SSH_USERNAME_REJECTED",
    "CLOUD_INIT_INCOMPLETE",
    "BOOTSTRAP_NOT_READY",
    "UNKNOWN",
}


class SshReadinessError(ValueError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _strict_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    seen: set[str] = set()
    for key, value in pairs:
        folded = key.casefold()
        if folded in seen:
            raise SshReadinessError(f"duplicate or case-ambiguous JSON key: {key}")
        seen.add(folded)
        result[key] = value
    return result


def strict_loads(value: str) -> Any:
    try:
        return json.loads(value, object_pairs_hook=_strict_pairs)
    except json.JSONDecodeError as exc:
        raise SshReadinessError("malformed JSON") from exc


def strict_load(path: Path) -> dict[str, Any]:
    try:
        result = strict_loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise SshReadinessError(f"cannot read artifact: {path.name}") from exc
    if not isinstance(result, dict):
        raise SshReadinessError("artifact root must be an object")
    return result


@dataclass(frozen=True)
class Observation:
    vm_created: bool = True
    public_ip_assigned: bool = True
    tcp: str = "OK"
    banner: str = "VALID"
    kex_started: bool = True
    host_key: str = "VERIFIED"
    auth_started: bool = True
    auth: str = "AUTHENTICATED"
    cloud_init: str = "COMPLETE"
    bootstrap_ready: bool = True


def classify(observation: Observation) -> str:
    if not observation.vm_created:
        return "VM_NOT_CREATED"
    if not observation.public_ip_assigned:
        return "PUBLIC_IP_MISSING"
    if observation.tcp == "TIMEOUT":
        return "TCP_TIMEOUT"
    if observation.tcp == "RESET":
        return "TCP_RESET"
    if observation.tcp != "OK":
        return "TCP_ERROR"
    if observation.banner == "MISSING":
        return "SSH_BANNER_NOT_RECEIVED"
    if observation.banner != "VALID":
        return "SSH_BANNER_MALFORMED"
    if not observation.kex_started:
        return "SSH_KEX_TIMEOUT"
    if observation.host_key == "ABSENT":
        return "SSH_HOST_KEY_ABSENT"
    if observation.host_key == "CHANGED":
        return "SSH_HOST_KEY_CHANGED"
    if observation.host_key != "VERIFIED":
        return "SSH_HOST_KEY_MISMATCH"
    if not observation.auth_started:
        return "SSH_AUTH_REJECTED"
    if observation.auth == "WRONG_USERNAME":
        return "SSH_USERNAME_REJECTED"
    if observation.auth != "AUTHENTICATED":
        return "SSH_AUTH_REJECTED"
    if observation.cloud_init != "COMPLETE":
        return "CLOUD_INIT_INCOMPLETE"
    if not observation.bootstrap_ready:
        return "BOOTSTRAP_NOT_READY"
    return "READY"


def _passed_stages(observation: Observation) -> set[str]:
    passed: set[str] = set()
    checks = (
        ("VM_CREATED", observation.vm_created),
        ("PUBLIC_IP_ASSIGNED", observation.public_ip_assigned),
        ("TCP22_REACHABLE", observation.tcp == "OK"),
        ("SSH_BANNER_RECEIVED", observation.banner == "VALID"),
        ("SSH_KEX_STARTED", observation.kex_started),
        ("SSH_HOST_KEY_VERIFIED", observation.host_key == "VERIFIED"),
        ("SSH_AUTH_STARTED", observation.auth_started),
        ("SSH_AUTHENTICATED", observation.auth == "AUTHENTICATED"),
        ("CLOUD_INIT_COMPLETE", observation.cloud_init == "COMPLETE"),
        ("ROUTEMIND_BOOTSTRAP_READY", observation.bootstrap_ready),
    )
    for stage, success in checks:
        if not success:
            break
        passed.add(stage)
    return passed


def build_artifact(
    *,
    execution_id: str,
    target: str,
    observation: Observation,
    attempts: Iterable[Mapping[str, Any]] = (),
    observed_at: str | None = None,
) -> dict[str, Any]:
    timestamp = observed_at or utc_now()
    attempt_list = list(attempts)
    terminal = classify(observation)
    passed = _passed_stages(observation)
    stages: list[dict[str, Any]] = []
    failure_seen = False
    for stage in STAGES:
        if stage in passed:
            status = "PASS"
        elif not failure_seen:
            status = "FAIL"
            failure_seen = True
        else:
            status = "NOT_REACHED"
        stages.append({"name": stage, "status": status, "observedAt": timestamp})
    if terminal == "READY":
        stages = [
            {"name": stage, "status": "PASS", "observedAt": timestamp} for stage in STAGES
        ]
    artifact = {
        "schema": SCHEMA,
        "executionId": execution_id,
        "target": target,
        "observedAt": timestamp,
        "retryCount": max(0, len(attempt_list) - 1),
        "terminalClassification": terminal,
        "rootCauseClaim": "UNKNOWN",
        "stages": stages,
        "attempts": attempt_list,
    }
    validate_artifact(artifact)
    return artifact


def validate_artifact(artifact: Mapping[str, Any]) -> None:
    if artifact.get("schema") != SCHEMA:
        raise SshReadinessError("artifact schema")
    if not str(artifact.get("executionId", "")) or not str(artifact.get("target", "")):
        raise SshReadinessError("artifact identity")
    terminal = artifact.get("terminalClassification")
    if terminal not in TERMINAL_CLASSIFICATIONS:
        raise SshReadinessError("terminal classification")
    if artifact.get("rootCauseClaim") != "UNKNOWN":
        raise SshReadinessError("root cause must remain UNKNOWN")
    stages = artifact.get("stages")
    if not isinstance(stages, list) or [item.get("name") for item in stages] != list(STAGES):
        raise SshReadinessError("stage order")
    if any(item.get("status") not in STAGE_STATUSES for item in stages):
        raise SshReadinessError("stage status")


def atomic_write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    os.replace(temporary, path)


def persist_target_artifact(root: Path, artifact: Mapping[str, Any]) -> Path:
    validate_artifact(artifact)
    target = str(artifact["target"])
    if not target.replace("-", "").replace("_", "").isalnum():
        raise SshReadinessError("unsafe target identity")
    path = root / "raw" / f"{target}-ssh-readiness.json"
    atomic_write_json(path, artifact)
    return path


def aggregate_artifacts(
    raw_paths: Mapping[str, Path],
    destination: Path,
    *,
    inject_failure: bool = False,
) -> dict[str, Any]:
    targets: dict[str, Any] = {}
    for target, path in raw_paths.items():
        try:
            artifact = strict_load(path)
            validate_artifact(artifact)
            targets[target] = {
                "artifact": path.name,
                "status": "AVAILABLE",
                "terminalClassification": artifact["terminalClassification"],
            }
        except SshReadinessError as exc:
            targets[target] = {
                "artifact": path.name,
                "status": "MALFORMED" if path.exists() else "MISSING",
                "errorClassification": exc.__class__.__name__,
            }
    if inject_failure:
        raise SshReadinessError("injected aggregation failure")
    status = "COMPLETE" if all(item["status"] == "AVAILABLE" for item in targets.values()) else "INCOMPLETE"
    summary = {
        "schema": "r4-vm-ssh-readiness-aggregate.v1",
        "generatedAt": utc_now(),
        "status": status,
        "rootCauseClaim": "UNKNOWN",
        "targets": targets,
    }
    atomic_write_json(destination, summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Aggregate SSH-readiness artifacts")
    parser.add_argument("--target", required=True)
    parser.add_argument("--artifact", required=True, type=Path)
    parser.add_argument("--destination", required=True, type=Path)
    arguments = parser.parse_args()
    aggregate_artifacts(
        {arguments.target: arguments.artifact}, arguments.destination
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
