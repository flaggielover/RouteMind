from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts/observability/r4-405-telemetry-export-v1.json"
COLLECTOR_PATH = ROOT / "infra/observability/otel-collector.yaml"

EXPECTED_BOUNDARIES = {"http", "messaging", "worker", "simulation", "experiment"}
EXPECTED_RAW_TENANT_ATTRIBUTES = {
    "routemind.tenant_id",
    "tenant.id",
    "enduser.id",
    "user.id",
    "courier.id",
    "principal.id",
}
EXPECTED_PIPELINE_PROCESSORS = ["memory_limiter", "attributes/tenant_safety", "batch"]


def load_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(f"{path.name} must contain an object")
    return payload


def digest(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def validate_contract(contract: dict[str, Any], collector: dict[str, Any]) -> list[str]:
    findings: list[str] = []
    if (
        contract.get("schemaVersion") != 1
        or contract.get("contractId") != "r4-405-telemetry-export-v1"
        or contract.get("status") != "LOCAL_IMPLEMENTED_TARGET_PENDING"
    ):
        findings.append("identity:contract")

    target = contract.get("target", {})
    if (
        target.get("provider") != "Vultr"
        or target.get("region") != "nrt"
        or target.get("dataResidency") != "Tokyo, Japan"
    ):
        findings.append("target:identity")
    if any(
        target.get(field) is not False
        for field in ("collectorVerified", "backendSelected", "productionCostVerified")
    ):
        findings.append("target:false_claim")

    correlation = contract.get("correlation", {})
    if (
        correlation.get("propagator") != "W3C Trace Context"
        or set(correlation.get("boundaries", [])) != EXPECTED_BOUNDARIES
        or "routemind.tenant_key" not in correlation.get("traceAttributes", [])
        or "traceparent" not in correlation.get("messageHeaders", [])
    ):
        findings.append("correlation:coverage")

    tenant = contract.get("tenantAttribution", {})
    if (
        tenant.get("algorithm") != "HMAC-SHA256"
        or tenant.get("tokenPrefix") != "rtk_"
        or tenant.get("digestHexCharacters") != 24
        or tenant.get("secretEnvironmentVariable") != "ROUTEMIND_TELEMETRY_ATTRIBUTION_KEY"
        or tenant.get("forwardedHeader") != "X-RouteMind-Tenant-Key"
        or tenant.get("forwardedHeaderTrust")
        != "private_authenticated_service_boundary_only"
    ):
        findings.append("tenant:pseudonym")
    if (
        tenant.get("maxActiveKeysPerRuntime") != 64
        or tenant.get("overflowKey") != "rtk_overflow"
        or tenant.get("unattributedKey") != "rtk_unattributed"
    ):
        findings.append("tenant:cardinality")
    if (
        tenant.get("rawTenantIdentifierExported") is not False
        or tenant.get("rawTenantIdentifierMetricLabel") is not False
    ):
        findings.append("tenant:raw_identifier")

    cardinality = contract.get("cardinality", {})
    forbidden_labels = set(cardinality.get("forbiddenMetricLabels", []))
    if (
        cardinality.get("metricSeriesPlanningCeilingPerRuntime") != 2048
        or "tenant_key" not in cardinality.get("approvedMetricLabels", [])
        or not {"request_id", "trace_id", "order_id", "courier_id"}.issubset(
            forbidden_labels
        )
    ):
        findings.append("cardinality:budget")

    cost = contract.get("costAttribution", {})
    if (
        cost.get("metric") != "routemind_telemetry_attributed_records_total"
        or cost.get("unit") != "logical_export_record"
        or set(cost.get("requiredLabels", []))
        != {"service", "signal", "operation", "tenant_key"}
        or set(cost.get("signals", [])) != {"metric", "trace"}
        or cost.get("vendorRateStatus") != "TARGET_BACKEND_REQUIRED"
        or cost.get("currencyCostClaim") is not False
    ):
        findings.append("cost:attribution")

    application = contract.get("applicationExporter", {})
    if (
        application.get("enabledByDefault") is not False
        or application.get("processor") != "batch"
        or application.get("maxQueueSize") != 2048
        or application.get("maxExportBatchSize") != 512
        or application.get("scheduleDelayMilliseconds") != 5000
        or application.get("exportTimeoutMilliseconds") != 10000
        or application.get("businessOutcomeOnFailure") != "UNCHANGED"
    ):
        findings.append("application:exporter")

    durable = contract.get("durableTruthBoundary", {})
    expected_durable = {
        "telemetryDurableAuthority": False,
        "exportCanBlockBusinessRequest": False,
        "exportCanChangeTransactionOutcome": False,
        "exportCanAcknowledgeMessage": False,
        "exportFailureCanTriggerBusinessRetry": False,
        "postgresqlRemainsDurableTruth": True,
    }
    if durable != expected_durable:
        findings.append("authority:durable_truth")

    collector_contract = contract.get("collector", {})
    if (
        collector_contract.get("configPath")
        != "infra/observability/otel-collector.yaml"
        or set(collector_contract.get("rawTenantAttributesRemoved", []))
        != EXPECTED_RAW_TENANT_ATTRIBUTES
    ):
        findings.append("collector:contract")
    findings.extend(_validate_collector(collector_contract, collector))

    qualification = contract.get("qualification", {})
    target_evidence = set(qualification.get("requiredTargetEvidence", []))
    if (
        qualification.get("targetStatus") != "TARGET_PENDING"
        or len(target_evidence) != 6
        or not any("leakage" in item for item in target_evidence)
        or not any("outage" in item for item in target_evidence)
        or not any("cost attribution" in item for item in target_evidence)
    ):
        findings.append("qualification:target")

    science = contract.get("scientificBoundary", {})
    if science != {
        "frozenR3_325": "E-PASS / X-PASS / S-FAIL / C-NO-CLAIM",
        "telemetryEvidenceIsScientificEvidence": False,
        "scientificClaimEstablished": False,
    }:
        findings.append("science:frozen_boundary")
    return sorted(set(findings))


def _validate_collector(contract: dict[str, Any], collector: dict[str, Any]) -> list[str]:
    findings: list[str] = []
    receiver = collector.get("receivers", {}).get("otlp", {}).get("protocols", {})
    if (
        receiver.get("grpc", {}).get("endpoint") != contract.get("otlpGrpcEndpoint")
        or receiver.get("http", {}).get("endpoint") != contract.get("otlpHttpEndpoint")
    ):
        findings.append("collector:receiver")

    processors = collector.get("processors", {})
    memory = processors.get("memory_limiter", {})
    batch = processors.get("batch", {})
    if (
        memory.get("limit_mib") != contract.get("memoryLimitMiB")
        or memory.get("spike_limit_mib") != contract.get("memorySpikeLimitMiB")
    ):
        findings.append("collector:memory")
    if (
        batch.get("send_batch_size") != contract.get("batchSize")
        or batch.get("send_batch_max_size") != contract.get("batchMaximumSize")
    ):
        findings.append("collector:batch")
    actions = processors.get("attributes/tenant_safety", {}).get("actions", [])
    removed = {
        action.get("key")
        for action in actions
        if isinstance(action, dict) and action.get("action") == "delete"
    }
    if removed != EXPECTED_RAW_TENANT_ATTRIBUTES:
        findings.append("collector:tenant_scrub")

    storage_name = "file_storage/telemetry_queue"
    storage = collector.get("extensions", {}).get(storage_name, {})
    if storage.get("directory") != contract.get("persistentQueueDirectory"):
        findings.append("collector:storage")
    exporter = collector.get("exporters", {}).get("otlphttp/target", {})
    if (
        exporter.get("endpoint")
        != "${env:" + str(contract.get("targetEndpointEnvironmentVariable")) + "}"
        or exporter.get("headers", {}).get("Authorization")
        != "${env:" + str(contract.get("authorizationEnvironmentVariable")) + "}"
    ):
        findings.append("collector:credentials")
    queue = exporter.get("sending_queue", {})
    if (
        queue.get("enabled") is not True
        or queue.get("queue_size") != contract.get("persistentQueueSize")
        or queue.get("storage") != storage_name
    ):
        findings.append("collector:queue")
    retry = exporter.get("retry_on_failure", {})
    if (
        retry.get("enabled") is not True
        or retry.get("max_elapsed_time")
        != f"{contract.get('retryMaximumElapsedSeconds')}s"
    ):
        findings.append("collector:retry")

    service = collector.get("service", {})
    if service.get("extensions") != [storage_name]:
        findings.append("collector:extensions")
    pipelines = service.get("pipelines", {})
    traces = pipelines.get("traces", {})
    metrics = pipelines.get("metrics", {})
    if (
        traces.get("receivers") != ["otlp"]
        or traces.get("processors") != EXPECTED_PIPELINE_PROCESSORS
        or traces.get("exporters") != ["otlphttp/target"]
    ):
        findings.append("collector:trace_pipeline")
    if (
        metrics.get("receivers") != ["otlp", "prometheus"]
        or metrics.get("processors") != EXPECTED_PIPELINE_PROCESSORS
        or metrics.get("exporters") != ["otlphttp/target"]
    ):
        findings.append("collector:metric_pipeline")
    return findings


def summary(contract: dict[str, Any], collector: dict[str, Any]) -> dict[str, Any]:
    return {
        "valid": True,
        "contractId": contract["contractId"],
        "contractDigest": digest(contract),
        "collectorDigest": digest(collector),
        "boundaryCount": len(contract["correlation"]["boundaries"]),
        "maxActiveTenantKeys": contract["tenantAttribution"]["maxActiveKeysPerRuntime"],
        "collectorVerified": contract["target"]["collectorVerified"],
        "productionCostVerified": contract["target"]["productionCostVerified"],
        "targetStatus": contract["qualification"]["targetStatus"],
    }


def main() -> int:
    contract = load_object(CONTRACT_PATH)
    collector = load_object(COLLECTOR_PATH)
    findings = validate_contract(contract, collector)
    if findings:
        for finding in findings:
            print(f"ERROR: {finding}")
        return 1
    print(json.dumps(summary(contract, collector), sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
