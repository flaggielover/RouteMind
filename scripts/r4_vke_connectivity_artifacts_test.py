from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

import r4_vke_connectivity_artifacts as artifacts


def complete_artifact(observer: str = "operator") -> dict:
    return {
        "schemaVersion": 2,
        "tool": "r4-vke-connectivity-diagnostic",
        "observer": observer,
        "executionId": "r4-diag-20990101t000000z-test123",
        "observedAt": "2099-01-01T00:00:00Z",
        "retryCount": 0,
        "endpoint": {"hostname": "cluster.example", "port": 6443},
        "proxy": {"environment": {}, "winhttp": "DIRECT", "systemProxy": "NOT_PROBED_BY_THIS_TOOL"},
        "probes": [],
        "phases": {
            phase: {"status": "RECORDED", "observedAt": "2099-01-01T00:00:00Z", "details": {}}
            for phase in artifacts.PHASES
        },
        "summary": {
            "dns": "DNS_OK",
            "tcp": "TCP_OK",
            "tlsHelloSent": True,
            "tls": "TLS_EOF",
            "http": "HTTP_NOT_ATTEMPTED",
            "terminalErrorClassification": "TLS_EOF",
        },
        "artifactStatus": "COMPLETE",
        "terminalErrorClassification": "TLS_EOF",
    }


class VkeArtifactTests(unittest.TestCase):
    def test_schema_rejects_case_variant_or_unknown_keys(self) -> None:
        candidate = complete_artifact()
        candidate["Observer"] = candidate.pop("observer")
        with self.assertRaises(artifacts.ProbeArtifactError):
            artifacts.validate_probe_artifact(candidate)

    def test_malformed_operator_does_not_delete_observer_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            operator = artifacts.persist_raw_then_parse(
                root / "operator.raw",
                root / "operator.json",
                "{malformed",
                observer="operator",
                execution_id="r4-diag-20990101t000000z-test123",
                observed_at="2099-01-01T00:00:00Z",
            )
            observer_path = root / "tokyo.json"
            observer_path.write_text(json.dumps(complete_artifact("tokyo-recovery")), encoding="utf-8")
            self.assertEqual(operator["artifactStatus"], "MALFORMED")
            self.assertTrue((root / "operator.raw").exists())
            self.assertTrue(observer_path.exists())

    def test_execution_failure_artifact_is_canonical(self) -> None:
        failure = artifacts.failure_artifact(
            observer="tokyo-recovery",
            execution_id="r4-diag-20990101t000000z-test123",
            observed_at="2099-01-01T00:00:00Z",
            retry_count=2,
            status="EXECUTION_FAILED",
            error_classification="SSH_EXIT_NONZERO",
        )
        self.assertEqual(artifacts.validate_probe_artifact(failure), failure)
        self.assertEqual(failure["summary"]["terminalErrorClassification"], "SSH_EXIT_NONZERO")

    def test_operator_execution_failure_is_retained(self) -> None:
        failure = artifacts.failure_artifact(
            observer="operator",
            execution_id="r4-diag-20990101t000000z-test123",
            observed_at="2099-01-01T00:00:00Z",
            retry_count=1,
            status="EXECUTION_FAILED",
            error_classification="PYTHON_EXIT_NONZERO",
        )
        self.assertEqual(failure["artifactStatus"], "EXECUTION_FAILED")
        self.assertEqual(failure["observer"], "operator")

    def test_observer_malformed_or_missing_fails_closed_without_aggregation_loss(self) -> None:
        operator = complete_artifact()
        malformed = copy.deepcopy(complete_artifact("tokyo-recovery"))
        malformed["phases"].pop("http")
        self.assertEqual(
            artifacts.aggregate_observers(operator, malformed)["classification"],
            "DIAGNOSTIC_INCOMPLETE",
        )
        self.assertEqual(
            artifacts.aggregate_observers(operator, None)["reason"],
            "OBSERVER_ARTIFACT_MISSING",
        )

    def test_aggregation_failure_does_not_change_observer_artifacts(self) -> None:
        operator = complete_artifact()
        tokyo = complete_artifact("tokyo-recovery")
        aggregate = artifacts.aggregate_observers(operator, tokyo)
        self.assertEqual(aggregate["classification"], "BOTH_OBSERVERS_FAILED")
        self.assertEqual(operator["artifactStatus"], "COMPLETE")
        self.assertEqual(tokyo["artifactStatus"], "COMPLETE")

    def test_aggregation_exception_fails_closed_without_erasing_inputs(self) -> None:
        operator = complete_artifact()
        tokyo = complete_artifact("tokyo-recovery")
        original = artifacts.validate_probe_artifact
        try:
            artifacts.validate_probe_artifact = lambda _value: (_ for _ in ()).throw(RuntimeError("aggregate"))  # type: ignore[assignment]
            result = artifacts.aggregate_observers(operator, tokyo)
        finally:
            artifacts.validate_probe_artifact = original  # type: ignore[assignment]
        self.assertEqual(result["classification"], "DIAGNOSTIC_INCOMPLETE")
        self.assertEqual(result["reason"], "AGGREGATION_FAILED")
        self.assertEqual(operator["artifactStatus"], "COMPLETE")
        self.assertEqual(tokyo["artifactStatus"], "COMPLETE")

    def test_operator_only_tls_failure_favors_operator_path(self) -> None:
        operator = complete_artifact("operator")
        tokyo = complete_artifact("tokyo-recovery")
        tokyo["summary"]["tls"] = "TLS_OK"
        tokyo["summary"]["http"] = "HTTP_OK"
        self.assertEqual(
            artifacts.aggregate_observers(operator, tokyo)["classification"],
            "OPERATOR_PATH_SUSPECTED",
        )


if __name__ == "__main__":
    unittest.main()
