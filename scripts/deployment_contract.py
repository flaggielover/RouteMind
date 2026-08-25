from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts/deployment/r4-401-vultr-tokyo-v1.json"
CATALOG_PATH = ROOT / "evidence/external/R4-401/vultr-public-catalog-2026-08-25.json"

EXPECTED_SERVICES = {
    "web",
    "business-api",
    "compute-api",
    "postgresql",
    "rabbitmq",
    "redis",
    "telemetry",
}
EXPECTED_SLOS = {
    "api-availability",
    "dispatch-latency",
    "event-publication-lag",
    "sse-freshness",
    "location-freshness",
    "in-region-postgresql-rpo",
    "in-region-postgresql-rto",
}
EXPECTED_FAILURE_DOMAINS = {
    "process_or_pod",
    "worker_node",
    "vke_control_plane",
    "stateful_replica_or_volume",
    "tokyo_region",
    "vultr_provider_or_account",
}
EXPECTED_COST_ITEMS = {
    "vke-worker-nodes",
    "backup-host",
    "load-balancer",
    "block-storage-gib",
    "vke-control-plane",
}


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(f"{path.name} must contain a JSON object")
    return payload


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _records_by_id(records: object) -> dict[str, dict[str, Any]]:
    if not isinstance(records, list):
        return {}
    return {
        record["id"]: record
        for record in records
        if isinstance(record, dict) and isinstance(record.get("id"), str)
    }


def validate_contract(
    contract: dict[str, Any],
    catalog: dict[str, Any],
    catalog_sha256: str,
) -> list[str]:
    findings: list[str] = []
    if contract.get("schemaVersion") != 1 or contract.get("contractId") != "r4-401-vultr-tokyo-v1":
        findings.append("identity:contract")
    if contract.get("status") != "FROZEN_APPROVED_TARGET_NOT_DEPLOYED":
        findings.append("identity:status")

    approval = contract.get("approval", {})
    if approval.get("approvedScope") != ["provider", "target_region", "data_residency"]:
        findings.append("approval:scope")
    for key in ("resourceCreationAuthorized", "spendAuthorized", "productionDeploymentAuthorized"):
        if approval.get(key) is not False:
            findings.append(f"approval:{key}")
    if (
        approval.get("provider") != "Vultr"
        or approval.get("targetRegion") != "nrt"
        or approval.get("dataResidency") != "Tokyo, Japan"
    ):
        findings.append("approval:target")

    evidence = contract.get("evidence", {})
    expected_catalog_path = "evidence/external/R4-401/vultr-public-catalog-2026-08-25.json"
    if evidence.get("catalogPath") != expected_catalog_path:
        findings.append("evidence:path")
    if evidence.get("catalogSha256") != catalog_sha256:
        findings.append("evidence:catalog_digest")
    if evidence.get("catalogCaptureMode") != "public_read_only_no_credentials":
        findings.append("evidence:capture_mode")
    if evidence.get("humanApprovalRecorded") is not True:
        findings.append("evidence:human_approval")

    if (
        catalog.get("schemaVersion") != 1
        or catalog.get("provider") != "Vultr"
        or catalog.get("captureMode") != "public_read_only_no_credentials"
    ):
        findings.append("catalog:identity")
    region = catalog.get("region", {})
    required_region_options = {"kubernetes", "load_balancers", "block_storage_high_perf"}
    if (
        region.get("id") != "nrt"
        or region.get("city") != "Tokyo"
        or region.get("country") != "JP"
        or not required_region_options.issubset(set(region.get("options", [])))
    ):
        findings.append("catalog:region")

    target = contract.get("target", {})
    if (
        target.get("provider") != "Vultr"
        or target.get("regionId") != "nrt"
        or target.get("city") != "Tokyo"
        or target.get("country") != "JP"
        or target.get("regionCount") != 1
    ):
        findings.append("target:region")
    if (
        target.get("maturity") != "TARGET_SELECTED_NOT_DEPLOYED"
        or target.get("productionVerified") is not False
        or target.get("externalAccountVerified") is not False
    ):
        findings.append("target:false_deployment_claim")

    ownership = contract.get("ownership", {})
    required_owners = {
        "accountAndBilling",
        "dataController",
        "platformOperations",
        "durableBusinessState",
        "optimizationSimulationResearch",
        "runtimeInfrastructure",
        "secretsAndKeys",
        "releaseApproval",
    }
    if set(ownership) != required_owners or any(not ownership.get(key) for key in required_owners):
        findings.append("ownership:coverage")
    if ownership.get("durableBusinessState") != "Java business API":
        findings.append("ownership:java_authority")
    if ownership.get("optimizationSimulationResearch") != "Python compute API":
        findings.append("ownership:python_boundary")

    topology = contract.get("topology", {})
    orchestrator = topology.get("orchestrator", {})
    if (
        orchestrator.get("product") != "Vultr Kubernetes Engine"
        or orchestrator.get("region") != "nrt"
        or orchestrator.get("haControlPlaneRequested") is not True
        or orchestrator.get("multiRegion") is not False
    ):
        findings.append("topology:orchestrator")
    plans = _records_by_id(catalog.get("plans"))
    workers = topology.get("workerPool", {})
    worker_plan = plans.get(workers.get("plan"), {})
    if (
        workers.get("initialNodes") != 3
        or workers.get("minimumNodes") != 3
        or workers.get("maximumNodes") != 6
        or workers.get("podAntiAffinityRequired") is not True
        or worker_plan.get("regionAvailable") != "nrt"
        or workers.get("totalInitialVcpu") != workers.get("initialNodes", 0) * worker_plan.get("vcpuCount", -1)
        or workers.get("totalInitialRamMiB") != workers.get("initialNodes", 0) * worker_plan.get("ramMiB", -1)
    ):
        findings.append("topology:worker_pool")
    backup = topology.get("backupHost", {})
    backup_plan = plans.get(backup.get("plan"), {})
    if backup.get("count") != 1 or backup.get("region") != "nrt" or backup.get("publicIngress") is not False or backup_plan.get("regionAvailable") != "nrt":
        findings.append("topology:backup_host")

    services = _records_by_id(topology.get("services"))
    if set(services) != EXPECTED_SERVICES:
        findings.append("topology:services")
    if services.get("postgresql", {}).get("durableAuthority") is not True:
        findings.append("topology:postgres_authority")
    if services.get("business-api", {}).get("durableAuthority") is not True:
        findings.append("topology:business_authority")
    if any(services.get(service_id, {}).get("durableAuthority") is not False for service_id in {"web", "compute-api", "rabbitmq", "redis", "telemetry"}):
        findings.append("topology:authority_leak")
    if any(services.get(service_id, {}).get("minimumReplicas", 0) < 2 for service_id in EXPECTED_SERVICES):
        findings.append("topology:replicas")

    storage = _records_by_id(topology.get("storageGiB"))
    if set(storage) != {"postgresql", "rabbitmq", "research-data", "backup-vault"}:
        findings.append("storage:coverage")
    storage_total = 0
    for item in storage.values():
        expected_total = item.get("volumeCount", -1) * item.get("perVolumeGiB", -1)
        if item.get("totalGiB") != expected_total:
            findings.append(f"storage:arithmetic:{item.get('id', 'unknown')}")
        storage_total += item.get("totalGiB", 0)
    if storage_total != 610:
        findings.append("storage:total")

    residency = contract.get("dataResidency", {})
    if residency.get("boundary") != "Tokyo, Japan (Vultr nrt)":
        findings.append("residency:boundary")
    required_in_region = {"PostgreSQL durable business state", "encrypted recovery packages"}
    if not required_in_region.issubset(set(residency.get("inRegionData", []))):
        findings.append("residency:in_region_data")
    required_forbidden = {"customer personal data", "courier trajectories", "tenant-scoped business events", "unencrypted recovery payloads"}
    if not required_forbidden.issubset(set(residency.get("forbiddenOutsideRegion", []))):
        findings.append("residency:outside_region")
    if residency.get("providerAutomaticBackups") != "disabled_until_backup_storage_location_is_contractually_verified":
        findings.append("residency:provider_backups")

    capacity = contract.get("capacityAssumptions", {})
    workload = capacity.get("qualificationWorkload", {})
    required_workload = {
        "dispatchSustainedRequestsPerSecond",
        "dispatchFiveMinuteBurstRequestsPerSecond",
        "concurrentSseConnections",
        "activeCourierLocations",
        "ordersPerDay",
    }
    if set(workload) != required_workload or any(not isinstance(workload.get(key), int) or workload[key] <= 0 for key in required_workload):
        findings.append("capacity:workload")
    baseline = capacity.get("baselineEvidence", {})
    if baseline.get("scope") != "loopback_regression_only_no_capacity_carry_forward":
        findings.append("capacity:baseline_scope")
    if capacity.get("validationTask") != "R4-407":
        findings.append("capacity:validation_task")

    slos = _records_by_id(contract.get("serviceLevelObjectives"))
    if set(slos) != EXPECTED_SLOS or any(slo.get("windowDays") != 30 for slo in slos.values()):
        findings.append("slo:coverage")
    availability = slos.get("api-availability", {})
    if availability.get("target") != 99.5 or availability.get("unit") != "percent_monthly" or availability.get("errorBudgetMinutes") != 216:
        findings.append("slo:availability")
    if slos.get("in-region-postgresql-rpo", {}).get("target") != 15 or slos.get("in-region-postgresql-rto", {}).get("target") != 120:
        findings.append("slo:recovery")

    failure_domains = _records_by_id(contract.get("failureDomains"))
    if set(failure_domains) != EXPECTED_FAILURE_DOMAINS:
        findings.append("failure_domain:coverage")
    region_failure = failure_domains.get("tokyo_region", {})
    if region_failure.get("mitigation") != "none in v1 because data is pinned to Tokyo" or "no committed regional RPO or RTO" not in region_failure.get("residual", ""):
        findings.append("failure_domain:single_region")

    cost = contract.get("costModel", {})
    items = _records_by_id(cost.get("recurringItems"))
    if set(items) != EXPECTED_COST_ITEMS:
        findings.append("cost:coverage")
    for item in items.values():
        if item.get("monthlyUsdCents") != item.get("quantity", -1) * item.get("unitMonthlyUsdCents", -1):
            findings.append(f"cost:arithmetic:{item.get('id', 'unknown')}")
    if items.get("vke-worker-nodes", {}).get("unitMonthlyUsdCents") != worker_plan.get("monthlyUsdCents"):
        findings.append("cost:worker_catalog")
    if items.get("backup-host", {}).get("unitMonthlyUsdCents") != backup_plan.get("monthlyUsdCents"):
        findings.append("cost:backup_catalog")
    published = catalog.get("publishedPricing", {})
    if items.get("load-balancer", {}).get("unitMonthlyUsdCents") != published.get("loadBalancerStartingMonthlyUsdCents"):
        findings.append("cost:load_balancer_catalog")
    if items.get("block-storage-gib", {}).get("quantity") != storage_total or items.get("block-storage-gib", {}).get("unitMonthlyUsdCents") != published.get("blockStorageMonthlyUsdCentsPerGiB"):
        findings.append("cost:storage_catalog")
    if items.get("vke-control-plane", {}).get("unitMonthlyUsdCents") != published.get("vkeControlPlaneMonthlyUsdCents"):
        findings.append("cost:vke_catalog")
    subtotal = sum(item.get("monthlyUsdCents", 0) for item in items.values())
    if cost.get("catalogSubtotalMonthlyUsdCents") != subtotal or subtotal != 23900:
        findings.append("cost:subtotal")
    if cost.get("planningCeilingMonthlyUsdCents") != subtotal + cost.get("contingencyMonthlyUsdCents", -1) or cost.get("planningCeilingMonthlyUsdCents") != 30000:
        findings.append("cost:ceiling")
    if cost.get("spendAuthorized") is not False or cost.get("priceStatus") != "PUBLIC_CATALOG_PLANNING_ESTIMATE_REQUOTE_BEFORE_SPEND":
        findings.append("cost:authorization")

    qualification = contract.get("qualificationGates", {})
    gates = set(qualification.get("beforeAnyProvisioning", []))
    if not any("credentials" in gate for gate in gates) or not any("spend approval" in gate for gate in gates):
        findings.append("qualification:before_provisioning")
    labels = qualification.get("requiredLabels", {})
    if labels.get("current") != "TARGET_SELECTED_NOT_DEPLOYED" or labels.get("production") != "not_claimed":
        findings.append("qualification:labels")

    science = contract.get("scientificBoundary", {})
    if science != {
        "frozenR3_325": "E-PASS / X-PASS / S-FAIL / C-NO-CLAIM",
        "round4DeploymentEvidenceIsScientificEvidence": False,
        "scientificClaimEstablished": False,
    }:
        findings.append("science:frozen_boundary")
    return sorted(set(findings))


def summary(contract: dict[str, Any], catalog_sha256: str) -> dict[str, Any]:
    return {
        "valid": True,
        "contractId": contract["contractId"],
        "contractDigest": digest(contract),
        "catalogSha256": catalog_sha256,
        "provider": contract["target"]["provider"],
        "region": contract["target"]["regionId"],
        "regionCount": contract["target"]["regionCount"],
        "sloCount": len(contract["serviceLevelObjectives"]),
        "planningCeilingMonthlyUsdCents": contract["costModel"]["planningCeilingMonthlyUsdCents"],
        "resourceCreationAuthorized": contract["approval"]["resourceCreationAuthorized"],
        "productionVerified": contract["target"]["productionVerified"],
    }


def main() -> int:
    contract = load_json(CONTRACT_PATH)
    catalog = load_json(CATALOG_PATH)
    catalog_sha256 = sha256_file(CATALOG_PATH)
    findings = validate_contract(contract, catalog, catalog_sha256)
    if findings:
        for finding in findings:
            print(f"ERROR: {finding}")
        return 1
    print(json.dumps(summary(contract, catalog_sha256), sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
