"""Canonical, failure-isolated probe artifacts for the v3 VKE diagnostic.

The module deliberately persists raw output before parsing or aggregation.  A
malformed or missing observer result therefore becomes an explicit artifact
and cannot erase the other observer's evidence.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

SCHEMA_VERSION = 2
OBSERVERS = {"operator", "tokyo-recovery"}
PHASES = ("dns", "tcp", "tls_client_hello", "tls_handshake", "http")
TOP_LEVEL_KEYS = {
    "schemaVersion",
    "observer",
    "executionId",
    "observedAt",
    "retryCount",
    "endpoint",
    "phases",
    "summary",
    "artifactStatus",
    "terminalErrorClassification",
    "tool",
    "proxy",
    "probes",
}
SUMMARY_KEYS = {
    "dns",
    "tcp",
    "tlsHelloSent",
    "tls",
    "http",
    "terminalErrorClassification",
}


class ProbeArtifactError(ValueError):
    """Raised when an artifact violates the canonical schema."""


def _require_mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ProbeArtifactError(f"{name} must be an object")
    return value


def validate_probe_artifact(value: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and return a shallow copy of one canonical observer artifact."""

    artifact = _require_mapping(value, "artifact")
    unknown = set(artifact) - TOP_LEVEL_KEYS
    missing = TOP_LEVEL_KEYS - set(artifact)
    if unknown:
        raise ProbeArtifactError(f"unknown top-level keys: {sorted(unknown)}")
    if missing:
        raise ProbeArtifactError(f"missing top-level keys: {sorted(missing)}")
    if artifact["schemaVersion"] != SCHEMA_VERSION:
        raise ProbeArtifactError("schemaVersion is not canonical")
    if artifact["observer"] not in OBSERVERS:
        raise ProbeArtifactError("observer identity is invalid")
    if not isinstance(artifact["executionId"], str) or not artifact["executionId"]:
        raise ProbeArtifactError("executionId is required")
    if not isinstance(artifact["observedAt"], str) or not artifact["observedAt"].endswith("Z"):
        raise ProbeArtifactError("observedAt must be a UTC timestamp")
    if not isinstance(artifact["retryCount"], int) or artifact["retryCount"] < 0:
        raise ProbeArtifactError("retryCount must be a non-negative integer")
    _require_mapping(artifact["endpoint"], "endpoint")
    phases = _require_mapping(artifact["phases"], "phases")
    if set(phases) != set(PHASES):
        raise ProbeArtifactError("phase keys are not canonical")
    for phase in PHASES:
        phase_value = _require_mapping(phases[phase], f"phases.{phase}")
        if set(phase_value) - {"status", "observedAt", "details"}:
            raise ProbeArtifactError(f"phase keys are not canonical: {phase}")
        if not isinstance(phase_value.get("status"), str) or not phase_value["status"]:
            raise ProbeArtifactError(f"phase status is missing: {phase}")
    summary = _require_mapping(artifact["summary"], "summary")
    if set(summary) != SUMMARY_KEYS:
        raise ProbeArtifactError("summary keys are not canonical")
    if artifact["artifactStatus"] not in {"COMPLETE", "EXECUTION_FAILED", "MALFORMED", "MISSING"}:
        raise ProbeArtifactError("artifactStatus is invalid")
    if not isinstance(artifact["terminalErrorClassification"], str):
        raise ProbeArtifactError("terminalErrorClassification is required")
    return dict(artifact)


def persist_raw_then_parse(
    raw_path: Path,
    artifact_path: Path,
    raw: str,
    *,
    observer: str,
    execution_id: str,
    observed_at: str,
    retry_count: int = 0,
) -> dict[str, Any]:
    """Persist raw output first, then parse/validate into the sanitized artifact."""

    raw_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text(raw, encoding="utf-8")
    try:
        parsed = json.loads(raw)
        artifact = validate_probe_artifact(parsed)
    except (OSError, json.JSONDecodeError, ProbeArtifactError) as exc:
        artifact = failure_artifact(
            observer=observer,
            execution_id=execution_id,
            observed_at=observed_at,
            retry_count=retry_count,
            status="MALFORMED",
            error_classification=type(exc).__name__,
        )
    artifact_path.write_text(json.dumps(artifact, sort_keys=True), encoding="utf-8")
    return artifact


def failure_artifact(
    *,
    observer: str,
    execution_id: str,
    observed_at: str,
    retry_count: int,
    status: str,
    error_classification: str,
) -> dict[str, Any]:
    """Build a complete canonical artifact for execution or transport failure."""

    if observer not in OBSERVERS:
        raise ProbeArtifactError("observer identity is invalid")
    artifact = {
        "schemaVersion": SCHEMA_VERSION,
        "tool": "r4-vke-connectivity-diagnostic",
        "observer": observer,
        "executionId": execution_id,
        "observedAt": observed_at,
        "retryCount": retry_count,
        "endpoint": {},
        "proxy": {"environment": {}, "winhttp": "NOT_RECORDED", "systemProxy": "NOT_PROBED_BY_THIS_TOOL"},
        "probes": [],
        "phases": {
            phase: {"status": "NOT_RECORDED", "observedAt": observed_at, "details": {}}
            for phase in PHASES
        },
        "summary": {
            "dns": "DNS_NOT_RECORDED",
            "tcp": "TCP_NOT_RECORDED",
            "tlsHelloSent": False,
            "tls": "TLS_NOT_RECORDED",
            "http": "HTTP_NOT_ATTEMPTED",
            "terminalErrorClassification": error_classification,
        },
        "artifactStatus": status,
        "terminalErrorClassification": error_classification,
    }
    return validate_probe_artifact(artifact)


def aggregate_observers(operator: Mapping[str, Any] | None, tokyo: Mapping[str, Any] | None) -> dict[str, Any]:
    """Aggregate only complete canonical artifacts; otherwise fail closed."""

    if operator is None or tokyo is None:
        return {"classification": "DIAGNOSTIC_INCOMPLETE", "reason": "OBSERVER_ARTIFACT_MISSING"}
    try:
        operator_value = validate_probe_artifact(operator)
        tokyo_value = validate_probe_artifact(tokyo)
    except ProbeArtifactError as exc:
        return {"classification": "DIAGNOSTIC_INCOMPLETE", "reason": type(exc).__name__}
    except Exception as exc:  # pragma: no cover - defensive aggregation boundary
        return {"classification": "DIAGNOSTIC_INCOMPLETE", "reason": "AGGREGATION_FAILED", "errorType": type(exc).__name__}
    if operator_value["artifactStatus"] != "COMPLETE" or tokyo_value["artifactStatus"] != "COMPLETE":
        return {"classification": "DIAGNOSTIC_INCOMPLETE", "reason": "OBSERVER_ARTIFACT_NOT_COMPLETE"}
    operator_tls = operator_value["summary"]["tls"]
    tokyo_tls = tokyo_value["summary"]["tls"]
    if operator_tls == "TLS_OK" and tokyo_tls == "TLS_OK":
        classification = "BOTH_OBSERVERS_TLS_OK"
    elif tokyo_tls == "TLS_OK":
        classification = "OPERATOR_PATH_SUSPECTED"
    elif operator_tls == "TLS_OK":
        classification = "TOKYO_PATH_SUSPECTED"
    else:
        classification = "BOTH_OBSERVERS_FAILED"
    return {"classification": classification, "operator": operator_value["summary"], "tokyoRecovery": tokyo_value["summary"]}
