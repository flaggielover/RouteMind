from __future__ import annotations

import copy
import unittest

import telemetry_export_contract as telemetry


class TelemetryExportContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = telemetry.load_object(telemetry.CONTRACT_PATH)
        self.collector = telemetry.load_object(telemetry.COLLECTOR_PATH)

    def assert_rejected(self, mutate, expected: str) -> None:  # type: ignore[no-untyped-def]
        contract = copy.deepcopy(self.contract)
        collector = copy.deepcopy(self.collector)
        mutate(contract, collector)
        self.assertIn(expected, telemetry.validate_contract(contract, collector))

    def test_contract_and_collector_are_valid_and_deterministic(self) -> None:
        self.assertEqual(telemetry.validate_contract(self.contract, self.collector), [])
        self.assertEqual(
            telemetry.digest(self.contract), telemetry.digest(copy.deepcopy(self.contract))
        )

    def test_target_cannot_be_promoted_without_external_evidence(self) -> None:
        self.assert_rejected(
            lambda contract, _collector: contract["target"].update(collectorVerified=True),
            "target:false_claim",
        )

    def test_round3_scientific_outcome_is_frozen(self) -> None:
        self.assert_rejected(
            lambda contract, _collector: contract["scientificBoundary"].update(
                frozenR3_325="E-PASS / X-PASS / S-PASS / C-PASS"
            ),
            "science:frozen_boundary",
        )

    def test_raw_tenant_attributes_must_be_removed(self) -> None:
        self.assert_rejected(
            lambda _contract, collector: collector["processors"][
                "attributes/tenant_safety"
            ]["actions"].pop(),
            "collector:tenant_scrub",
        )

    def test_collector_queue_is_bounded_and_persistent(self) -> None:
        self.assert_rejected(
            lambda _contract, collector: collector["exporters"]["otlphttp/target"][
                "sending_queue"
            ].update(queue_size=0),
            "collector:queue",
        )
        self.assert_rejected(
            lambda _contract, collector: collector["exporters"]["otlphttp/target"][
                "sending_queue"
            ].pop("storage"),
            "collector:queue",
        )

    def test_application_export_cannot_become_business_authority(self) -> None:
        self.assert_rejected(
            lambda contract, _collector: contract["durableTruthBoundary"].update(
                exportCanChangeTransactionOutcome=True
            ),
            "authority:durable_truth",
        )

    def test_collector_credentials_remain_environment_only(self) -> None:
        self.assert_rejected(
            lambda _contract, collector: collector["exporters"]["otlphttp/target"][
                "tls"
            ].update(insecure_skip_verify=True),
            "collector:credentials",
        )

    def test_logs_and_mutual_tls_are_required(self) -> None:
        self.assert_rejected(
            lambda _contract, collector: collector["service"]["pipelines"].pop("logs"),
            "collector:log_pipeline",
        )
        self.assert_rejected(
            lambda _contract, collector: collector["receivers"]["otlp"]["protocols"][
                "grpc"
            ].pop("tls"),
            "collector:receiver",
        )

    def test_all_five_correlation_boundaries_are_required(self) -> None:
        self.assert_rejected(
            lambda contract, _collector: contract["correlation"]["boundaries"].remove(
                "worker"
            ),
            "correlation:coverage",
        )


if __name__ == "__main__":
    unittest.main()
