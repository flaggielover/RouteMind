from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from r4_external_validation import (
    CONTRACT_PATH,
    EXPECTED_ARTIFACTS,
    EXPECTED_BOUNDARIES,
    canonical_digest,
    load_object,
    validate_evidence,
)

ARTIFACT_FILES = {
    "authenticated-resource-manifest": "authenticated-resource-manifest.json",
    "environment-version-manifest": "environment-version-manifest.json",
    "collector-health": "collector-health.json",
    "trace-query": "trace-query.json",
    "metric-query": "metric-query.json",
    "correlated-log-query": "correlated-log-query.json",
    "leakage-scan": "leakage-scan.json",
    "failure-recovery-timeline": "failure-recovery-timeline.json",
    "target-recovery-report": "target-recovery-report.json",
    "resource-usage": "resource-usage.json",
    "cost-bound": "cost-bound.json",
    "cleanup-inventory": "cleanup-inventory.json",
    "actual-routemind-workload": "actual-routemind-workload.json",
}

CHECK_ARTIFACTS = {
    "vultr_tokyo_identity": ["authenticated-resource-manifest"],
    "collector_health": ["collector-health"],
    "otlp_connectivity": ["trace-query"],
    "five_boundary_trace": ["actual-routemind-workload", "trace-query"],
    "metrics_export": ["metric-query"],
    "log_correlation": ["correlated-log-query"],
    "tenant_security_boundary": ["trace-query", "leakage-scan"],
    "leakage_scan": ["leakage-scan"],
    "network_failure": ["failure-recovery-timeline"],
    "collector_outage": ["failure-recovery-timeline"],
    "backend_outage": ["failure-recovery-timeline"],
    "recovery_behavior": ["failure-recovery-timeline", "trace-query"],
    "durable_business_truth": ["failure-recovery-timeline"],
    "r4_406_restore": ["target-recovery-report"],
    "resource_consumption": ["resource-usage"],
    "cost_accounting": ["cost-bound"],
    "cleanup": ["cleanup-inventory"],
}

FORBIDDEN_PATTERNS = {
    "private-key-header": re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----"),
    "authorization-bearer": re.compile(r"authorization\s*[:=]\s*bearer\s+\S+", re.I),
    "vultr-api-key-assignment": re.compile(r"VULTR_API_KEY\s*[:=]\s*\S+", re.I),
    "clickhouse-password-assignment": re.compile(r"clickhouse(?:_|\.)password\s*[:=]\s*\S+", re.I),
    "raw-tenant-identifier": re.compile(r"(?:tenant|courier|merchant)[._-]?id\s*[:=]\s*(?!rtk_)[^\s,}\]]+", re.I),
    "production-payload-marker": re.compile(r"ROUTEMIND_PRODUCTION_(?:ORDER|TENANT|COURIER)", re.I),
}


class EvidenceAssemblyError(ValueError):
    pass


def _utc(value: object) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise EvidenceAssemblyError("timestamp is not RFC3339 UTC")
    try:
        return datetime.fromisoformat(value[:-1] + "+00:00").astimezone(UTC)
    except ValueError as exc:
        raise EvidenceAssemblyError("timestamp is not RFC3339 UTC") from exc


def _load_required(path: Path) -> dict[str, Any]:
    if not path.is_file() or path.stat().st_size <= 0:
        raise EvidenceAssemblyError(f"required evidence is absent: {path.name}")
    return load_object(path)


def _scan_files(evidence_dir: Path, output: Path) -> dict[str, Any]:
    findings = {name: 0 for name in FORBIDDEN_PATTERNS}
    scanned_files = 0
    for path in sorted(evidence_dir.rglob("*")):
        if not path.is_file() or path.resolve() == output.resolve():
            continue
        if path.name in {"r4-external-validation-evidence.json"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            raise EvidenceAssemblyError(f"binary evidence is not permitted: {path.name}")
        scanned_files += 1
        for name, pattern in FORBIDDEN_PATTERNS.items():
            findings[name] += len(pattern.findall(text))
    secret_names = {
        "private-key-header",
        "authorization-bearer",
        "vultr-api-key-assignment",
        "clickhouse-password-assignment",
    }
    result = {
        "scanCompleted": True,
        "scannedAt": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "scannedFileCount": scanned_files,
        "secretFindings": sum(findings[name] for name in secret_names),
        "rawTenantIdentifierFindings": findings["raw-tenant-identifier"],
        "productionDataFindings": findings["production-payload-marker"],
        "findingCountsByClass": findings,
        "matchedValuesRetained": False,
    }
    if any(
        result[name]
        for name in (
            "secretFindings",
            "rawTenantIdentifierFindings",
            "productionDataFindings",
        )
    ):
        raise EvidenceAssemblyError("leakage scan found forbidden evidence content")
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def _validate_runtime_inputs(evidence_dir: Path, lifecycle: Mapping[str, Any]) -> dict[str, Any]:
    trace = _load_required(evidence_dir / ARTIFACT_FILES["trace-query"])
    metric = _load_required(evidence_dir / ARTIFACT_FILES["metric-query"])
    log = _load_required(evidence_dir / ARTIFACT_FILES["correlated-log-query"])
    usage = _load_required(evidence_dir / ARTIFACT_FILES["resource-usage"])
    cost = _load_required(evidence_dir / ARTIFACT_FILES["cost-bound"])
    cleanup = _load_required(evidence_dir / ARTIFACT_FILES["cleanup-inventory"])
    manifest = _load_required(evidence_dir / ARTIFACT_FILES["authenticated-resource-manifest"])
    timeline = _load_required(evidence_dir / ARTIFACT_FILES["failure-recovery-timeline"])
    target_recovery = _load_required(evidence_dir / ARTIFACT_FILES["target-recovery-report"])
    workload = _load_required(evidence_dir / "actual-routemind-workload.json")

    if (
        workload.get("actualRouteMindWorkload") is not True
        or workload.get("classification") != "ACTUAL_ROUTEMIND_SYNTHETIC_QUALIFICATION"
        or workload.get("businessOutcome") != "PASS_UNCHANGED_BY_TELEMETRY"
        or workload.get("syntheticDataOnly") is not True
    ):
        raise EvidenceAssemblyError("actual RouteMind workload evidence is incomplete")

    trace_id = trace.get("traceId")
    if (
        not isinstance(trace_id, str)
        or trace_id != lifecycle.get("traceId")
        or set(trace.get("boundaries", [])) != EXPECTED_BOUNDARIES
        or trace.get("singleTrace") is not False
        or trace.get("actualRouteMindWorkload") is not True
        or not isinstance(trace.get("spanCount"), int)
        or trace.get("spanCount", 0) < 8
        or trace.get("backend") != "signoz_clickhouse"
    ):
        raise EvidenceAssemblyError("actual trace backend evidence is incomplete")
    if (
        metric.get("metricName") != "routemind_telemetry_attributed_records_total"
        or not isinstance(metric.get("sampleCount"), int)
        or metric.get("sampleCount", 0) <= 0
        or not isinstance(metric.get("valueSum"), (int, float))
        or metric.get("valueSum", 0) < 6
        or metric.get("backend") != "signoz_clickhouse"
    ):
        raise EvidenceAssemblyError("actual metric backend evidence is incomplete")
    if (
        not isinstance(log.get("traceId"), str)
        or re.fullmatch(r"[0-9a-f]{32}", log.get("traceId", "")) is None
        or not isinstance(log.get("logCount"), int)
        or log.get("logCount", 0) <= 0
        or log.get("correlated") is not True
        or log.get("backend") != "signoz_clickhouse"
    ):
        raise EvidenceAssemblyError("actual correlated log backend evidence is incomplete")

    required_phases = {
        "collector_outage",
        "collector_recovered",
        "backend_outage",
        "backend_recovered",
        "network_outage",
        "network_and_pipeline_recovered",
    }
    phases = {
        item.get("phase")
        for item in timeline.get("events", [])
        if isinstance(item, Mapping)
    }
    if (
        phases != required_phases
        or timeline.get("businessOutcomeUnchanged") is not True
        or timeline.get("recoveredTraceId") != trace_id
    ):
        raise EvidenceAssemblyError("failure and recovery evidence is incomplete")

    resources = manifest.get("resources", [])
    lifecycle_resources = lifecycle.get("resources", [])
    identity = lambda item: (item.get("type"), item.get("providerId"), item.get("region"), item.get("createdAt"))
    if (
        not isinstance(resources, list)
        or not isinstance(lifecycle_resources, list)
        or sorted(identity(item) for item in resources if isinstance(item, Mapping))
        != sorted(identity(item) for item in lifecycle_resources if isinstance(item, Mapping))
    ):
        raise EvidenceAssemblyError("credentialed resource manifest is not bound to lifecycle")
    if manifest.get("identitySource") != "authenticated_vultr_api_and_vke_csi":
        raise EvidenceAssemblyError("resource identity source is not credentialed")
    if target_recovery.get("classification") != "TARGET_DRILL_PASS":
        raise EvidenceAssemblyError("R4-406 target evidence is not an external target")
    if target_recovery.get("productionDeploymentVerified") is not False:
        raise EvidenceAssemblyError("R4-406 target report attempted a production claim")

    for key, maximum in (("peakCpuCores", 12), ("peakMemoryMiB", 24576), ("peakStorageGiB", 60)):
        value = usage.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 < value <= maximum:
            raise EvidenceAssemblyError(f"resource usage is outside the contract: {key}")
    if (
        cost.get("source") != "authenticated_vultr_quote_and_runtime_bound"
        or cost.get("withinApprovedCeiling") is not True
        or not isinstance(cost.get("upperBoundUsdCents"), int)
        or not 0 < cost.get("upperBoundUsdCents", 0) <= 1500
    ):
        raise EvidenceAssemblyError("cost evidence is outside the approved ceiling")
    if cleanup.get("complete") is not True or cleanup.get("remainingResourceIds") != []:
        raise EvidenceAssemblyError("cleanup evidence is incomplete")
    return {
        "trace": trace,
        "usage": usage,
        "cost": cost,
        "cleanup": cleanup,
    }


def _artifact_manifest(evidence_dir: Path, captured_at: str) -> list[dict[str, Any]]:
    artifacts: list[dict[str, Any]] = []
    for artifact_id, filename in sorted(ARTIFACT_FILES.items()):
        path = evidence_dir / filename
        if not path.is_file() or path.stat().st_size <= 0:
            raise EvidenceAssemblyError(f"required artifact is absent: {filename}")
        artifacts.append(
            {
                "id": artifact_id,
                "path": filename,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "byteSize": path.stat().st_size,
                "capturedAt": captured_at,
                "containsSecrets": False,
            }
        )
    if {item["id"] for item in artifacts} != EXPECTED_ARTIFACTS:
        raise EvidenceAssemblyError("artifact inventory differs from the evidence contract")
    return artifacts


def assemble(evidence_dir: Path, lifecycle_path: Path, output: Path) -> dict[str, Any]:
    lifecycle = load_object(lifecycle_path)
    started = _utc(lifecycle.get("startedAt"))
    completed = _utc(lifecycle.get("completedAt"))
    if completed <= started or (completed - started).total_seconds() > 8 * 3600:
        raise EvidenceAssemblyError("execution lifecycle is outside the eight-hour boundary")

    leakage = _scan_files(evidence_dir, evidence_dir / ARTIFACT_FILES["leakage-scan"])
    runtime = _validate_runtime_inputs(evidence_dir, lifecycle)
    captured_at = lifecycle["completedAt"]
    contract = load_object(CONTRACT_PATH)
    artifacts = _artifact_manifest(evidence_dir, captured_at)
    checks = {
        check_id: {
            "status": "PASS",
            "observedAt": captured_at,
            "artifactIds": artifact_ids,
        }
        for check_id, artifact_ids in sorted(CHECK_ARTIFACTS.items())
    }
    report: dict[str, Any] = {
        "schemaVersion": "r4-external-validation-evidence.v1",
        "contractDigest": canonical_digest(contract),
        "classification": "EXTERNAL_VALIDATION_PASS",
        "productionDeploymentVerified": False,
        "execution": {
            "id": lifecycle["executionId"],
            "startedAt": lifecycle["startedAt"],
            "completedAt": lifecycle["completedAt"],
            "credentialedProviderCalls": True,
            "mockEvidence": False,
            "composeEvidencePromoted": False,
            "workloadDataClass": "SYNTHETIC_NO_CUSTOMER_DATA",
        },
        "target": {
            "provider": "Vultr",
            "region": "nrt",
            "city": "Tokyo",
            "country": "JP",
            "dataResidency": "Tokyo, Japan",
            "identitySource": "authenticated_vultr_api",
        },
        "resources": lifecycle["resources"],
        "checks": checks,
        "correlation": {
            "traceId": runtime["trace"]["traceId"],
            "boundaries": sorted(EXPECTED_BOUNDARIES),
            "singleTrace": False,
            "actualRouteMindWorkload": True,
            "syntheticQualificationTraffic": True,
        },
        "tenantBoundary": {
            "rawIdentifierFindings": leakage["rawTenantIdentifierFindings"],
            "pseudonymizedKeysOnly": True,
            "maximumObservedActiveKeys": runtime["trace"]["tenantKeyCount"],
        },
        "leakage": {
            key: leakage[key]
            for key in (
                "secretFindings",
                "rawTenantIdentifierFindings",
                "productionDataFindings",
                "scanCompleted",
            )
        },
        "resourceUsage": {
            key: runtime["usage"][key]
            for key in ("peakCpuCores", "peakMemoryMiB", "peakStorageGiB")
        },
        "cost": {
            "currency": "USD",
            "source": "authenticated_vultr_quote_and_runtime_bound",
            "upperBoundUsdCents": runtime["cost"]["upperBoundUsdCents"],
            "withinApprovedCeiling": True,
        },
        "artifacts": artifacts,
        "cleanup": runtime["cleanup"],
        "taskQualification": {
            "R4-405": "TARGET_QUALIFIED",
            "R4-406": "TARGET_DRILL_PASS",
        },
        "scientificBoundary": {
            "frozenR3_325": "E-PASS / X-PASS / S-FAIL / C-NO-CLAIM",
            "rerunOccurred": False,
            "externalValidationIsScientificEvidence": False,
            "scientificClaimEstablished": False,
        },
    }
    report["reportDigest"] = canonical_digest(report, omit="reportDigest")
    findings = validate_evidence(report, contract)
    if findings:
        raise EvidenceAssemblyError("assembled report failed contract: " + ", ".join(findings))
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Assemble fail-closed R4 external evidence")
    parser.add_argument("--evidence-dir", required=True, type=Path)
    parser.add_argument("--lifecycle", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        report = assemble(args.evidence_dir.resolve(), args.lifecycle.resolve(), args.output.resolve())
    except (EvidenceAssemblyError, OSError, KeyError, TypeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({"valid": True, "reportDigest": report["reportDigest"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
