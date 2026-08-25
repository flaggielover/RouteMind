from __future__ import annotations

import hashlib
import json
from datetime import datetime
from collections.abc import Mapping
from typing import Any

SCHEMA_VERSION = "r4-406.v1"
LOCAL_CLASSIFICATION = "LOCAL_DRILL_PASS_TARGET_PENDING"
TARGET_CLASSIFICATION = "TARGET_DRILL_PASS"
TARGET_PROVIDER = "Vultr"
TARGET_REGION = "nrt"
RPO_LIMIT_SECONDS = 15 * 60
RTO_LIMIT_SECONDS = 120 * 60

REQUIRED_CHECKS = frozenset(
    {
        "postgres_restore",
        "tenant_isolation",
        "audit_continuity",
        "outbox_restore",
        "inbox_restore",
        "rabbitmq_topology_restore",
        "outbox_replay",
        "redis_snapshot_restore",
        "redis_projection_rebuild",
        "reconciliation_evidence",
        "rollback_restore",
    }
)
REQUIRED_SERVICES = frozenset({"postgres", "rabbitmq", "redis"})


def canonical_digest(value: Mapping[str, Any]) -> str:
    payload = dict(value)
    payload.pop("reportDigest", None)
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(character in "0123456789abcdef" for character in value)


def _is_utc_timestamp(value: object) -> bool:
    if not isinstance(value, str) or not value.endswith("Z"):
        return False
    try:
        datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        return False
    return True


def external_identity_digest(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def validate_external_identity(value: object) -> tuple[str, ...]:
    if not isinstance(value, Mapping):
        return ("target_external_identity",)
    findings: list[str] = []
    if (
        value.get("provider") != TARGET_PROVIDER
        or value.get("region") != TARGET_REGION
        or value.get("resourceType") != "Vultr Cloud Compute"
        or not isinstance(value.get("resourceId"), str)
        or len(value.get("resourceId", "")) < 8
    ):
        findings.append("target_external_identity")
    if (
        value.get("credentialedProviderEvidence") is not True
        or value.get("workloadDataClass") != "SYNTHETIC_NO_CUSTOMER_DATA"
        or not _is_utc_timestamp(value.get("observedAt"))
        or not _is_sha256(value.get("executionManifestSha256"))
    ):
        findings.append("target_external_evidence")
    return tuple(sorted(set(findings)))


def validate_report(report: Mapping[str, Any], *, require_target: bool = False) -> tuple[str, ...]:
    findings: list[str] = []
    if report.get("schemaVersion") != SCHEMA_VERSION:
        findings.append("schema_version")

    environment = report.get("environment")
    if not isinstance(environment, Mapping):
        findings.append("environment")
        environment = {}
    mode = environment.get("mode")
    provider = environment.get("provider")
    region = environment.get("region")
    target_evidence = environment.get("targetEvidenceSha256")
    external_identity = report.get("externalIdentity")

    if mode == "target":
        if (
            provider != TARGET_PROVIDER
            or region != TARGET_REGION
            or not _is_sha256(target_evidence)
            or not isinstance(external_identity, Mapping)
            or target_evidence != external_identity_digest(external_identity)
        ):
            findings.append("target_identity")
        findings.extend(validate_external_identity(external_identity))
        expected_classification = TARGET_CLASSIFICATION
    elif mode == "local-ci":
        if (
            provider != "Docker"
            or region != "loopback"
            or target_evidence is not None
            or external_identity is not None
        ):
            findings.append("local_identity")
        expected_classification = LOCAL_CLASSIFICATION
    else:
        findings.append("environment_mode")
        expected_classification = None

    if require_target and mode != "target":
        findings.append("target_evidence_required")
    if report.get("classification") != expected_classification:
        findings.append("classification")
    if report.get("productionDeploymentVerified") is not False:
        findings.append("production_claim")

    safety = report.get("safety")
    if not isinstance(safety, Mapping):
        findings.append("safety")
        safety = {}
    if safety.get("scope") != "isolated_ephemeral_only" or safety.get("productionDataUsed") is not False:
        findings.append("safety_scope")
    if safety.get("sourceContainersDestroyedBeforeRestore") is not True:
        findings.append("failure_boundary")

    artifacts = report.get("artifacts")
    if not isinstance(artifacts, list):
        findings.append("artifacts")
        artifacts = []
    services = {artifact.get("service") for artifact in artifacts if isinstance(artifact, Mapping)}
    if services != REQUIRED_SERVICES:
        findings.append("artifact_services")
    for artifact in artifacts:
        if not isinstance(artifact, Mapping) or not _is_sha256(artifact.get("sha256")) or not isinstance(artifact.get("byteSize"), int) or artifact.get("byteSize", 0) <= 0:
            findings.append("artifact_integrity")
            break

    checks = report.get("checks")
    if not isinstance(checks, Mapping) or set(checks) != REQUIRED_CHECKS:
        findings.append("check_set")
    elif any(value is not True for value in checks.values()):
        findings.append("check_failure")

    metrics = report.get("metrics")
    if not isinstance(metrics, Mapping):
        findings.append("metrics")
        metrics = {}
    rpo = metrics.get("rpoSeconds")
    rto = metrics.get("rtoSeconds")
    if not isinstance(rpo, (int, float)) or isinstance(rpo, bool) or rpo < 0:
        findings.append("rpo")
    if not isinstance(rto, (int, float)) or isinstance(rto, bool) or rto <= 0:
        findings.append("rto")
    if mode == "target" and isinstance(rpo, (int, float)) and rpo > RPO_LIMIT_SECONDS:
        findings.append("target_rpo_exceeded")
    if mode == "target" and isinstance(rto, (int, float)) and rto > RTO_LIMIT_SECONDS:
        findings.append("target_rto_exceeded")

    continuity = report.get("continuity")
    if not isinstance(continuity, Mapping):
        findings.append("continuity")
        continuity = {}
    if continuity.get("tenantCount") != 2 or continuity.get("sourceDigest") != continuity.get("restoredDigest") or continuity.get("sourceDigest") != continuity.get("rollbackDigest"):
        findings.append("durable_continuity")
    if not _is_sha256(continuity.get("sourceDigest")):
        findings.append("continuity_digest")

    rollback = report.get("rollback")
    if not isinstance(rollback, Mapping) or rollback.get("ack") != "required" or not _is_sha256(rollback.get("manifestDigest")):
        findings.append("rollback_manifest")

    actual_digest = report.get("reportDigest")
    if not _is_sha256(actual_digest) or actual_digest != canonical_digest(report):
        findings.append("report_digest")
    return tuple(sorted(set(findings)))


def qualify_report(report: Mapping[str, Any]) -> str:
    findings = validate_report(report, require_target=True)
    return TARGET_CLASSIFICATION if not findings else "TARGET_NOT_QUALIFIED"
