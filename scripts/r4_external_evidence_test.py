from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from r4_external_evidence import EvidenceAssemblyError, assemble
from r4_external_validation import CONTRACT_PATH, load_object, validate_evidence

STAMP = "2026-08-25T12:00:00Z"
COMPLETED = "2026-08-25T13:00:00Z"
TRACE_ID = "a" * 32


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def resources(*, cleaned: bool) -> list[dict[str, object]]:
    return [
        {
            "type": resource_type,
            "providerId": provider_id,
            "region": "nrt",
            "createdAt": STAMP,
            "deletedAt": COMPLETED if cleaned else None,
            "cleanupVerified": cleaned,
        }
        for resource_type, provider_id in (
            ("Vultr Kubernetes Engine", "vke-12345678"),
            ("Vultr Cloud Compute", "instance-12345678"),
            ("Vultr Block Storage", "block-12345678"),
        )
    ]


class EvidenceAssemblyTests(unittest.TestCase):
    def fixture(self, root: Path) -> tuple[Path, Path, Path]:
        evidence = root / "sanitized-evidence"
        evidence.mkdir()
        lifecycle = root / "lifecycle.json"
        output = root / "report.json"
        write_json(evidence / "authenticated-resource-manifest.json", {"identitySource": "authenticated_vultr_api_and_vke_csi", "resources": resources(cleaned=False)})
        write_json(evidence / "environment-version-manifest.json", {"capturedAt": COMPLETED, "versions": ["pinned"]})
        write_json(evidence / "collector-health.json", {"observedAt": STAMP, "readyReplicas": 2})
        write_json(evidence / "trace-query.json", {"backend": "signoz_clickhouse", "traceId": TRACE_ID, "boundaries": ["http", "messaging", "worker", "simulation", "experiment"], "spanCount": 8, "tenantKeyCount": 1, "singleTrace": False, "actualRouteMindWorkload": True})
        write_json(evidence / "metric-query.json", {"backend": "signoz_clickhouse", "metricName": "routemind_telemetry_attributed_records_total", "sampleCount": 6, "valueSum": 6})
        write_json(evidence / "correlated-log-query.json", {"backend": "signoz_clickhouse", "traceId": "b" * 32, "logCount": 1, "correlated": True})
        write_json(
            evidence / "failure-recovery-timeline.json",
            {
                "events": [{"phase": phase, "observedAt": STAMP} for phase in ("collector_outage", "collector_recovered", "backend_outage", "backend_recovered", "network_outage", "network_and_pipeline_recovered")],
                "businessOutcomeUnchanged": True,
                "recoveredTraceId": TRACE_ID,
            },
        )
        write_json(evidence / "target-recovery-report.json", {"classification": "TARGET_DRILL_PASS", "productionDeploymentVerified": False})
        write_json(evidence / "actual-routemind-workload.json", {"classification": "ACTUAL_ROUTEMIND_SYNTHETIC_QUALIFICATION", "actualRouteMindWorkload": True, "businessOutcome": "PASS_UNCHANGED_BY_TELEMETRY", "syntheticDataOnly": True})
        write_json(evidence / "resource-usage.json", {"peakCpuCores": 2.5, "peakMemoryMiB": 4096, "peakStorageGiB": 50})
        write_json(evidence / "cost-bound.json", {"source": "authenticated_vultr_quote_and_runtime_bound", "upperBoundUsdCents": 500, "withinApprovedCeiling": True})
        write_json(evidence / "cleanup-inventory.json", {"complete": True, "credentialedInventoryCheck": True, "remainingResourceIds": [], "localPrivateKeysDeleted": True, "kubeconfigDeleted": True, "verifiedAt": COMPLETED})
        write_json(lifecycle, {"executionId": "r4-ext-20260825t120000z-abcdef1234", "startedAt": STAMP, "completedAt": COMPLETED, "traceId": TRACE_ID, "resources": resources(cleaned=True)})
        return evidence, lifecycle, output

    def test_assembles_and_validates_complete_real_shape(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            evidence, lifecycle, output = self.fixture(Path(directory))
            report = assemble(evidence, lifecycle, output)
            self.assertEqual((), validate_evidence(report, load_object(CONTRACT_PATH)))
            self.assertEqual("EXTERNAL_VALIDATION_PASS", report["classification"])

    def test_rejects_probe_shape_as_backend_query(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            evidence, lifecycle, output = self.fixture(Path(directory))
            write_json(evidence / "metric-query.json", {"businessOutcome": "PASS_UNCHANGED_BY_TELEMETRY"})
            with self.assertRaises(EvidenceAssemblyError):
                assemble(evidence, lifecycle, output)

    def test_rejects_secret_material_in_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            evidence, lifecycle, output = self.fixture(Path(directory))
            marker = "-" * 5 + "BEGIN " + "PRIVATE KEY" + "-" * 5
            (evidence / "unsafe.txt").write_text(f"{marker}\nnot-a-real-key\n", encoding="utf-8")
            with self.assertRaises(EvidenceAssemblyError):
                assemble(evidence, lifecycle, output)


if __name__ == "__main__":
    unittest.main()
