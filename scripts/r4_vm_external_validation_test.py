from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from r4_vm_external_validation import (
    CONTRACT_PATH,
    DEPLOYMENT_CONTRACT_PATH,
    IAC_ROOT,
    canonical_digest,
    load_object,
    validate_contract,
    validate_iac_sources,
)


class VmExternalValidationContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = load_object(CONTRACT_PATH)
        self.deployment = load_object(DEPLOYMENT_CONTRACT_PATH)

    def assert_invalid(self, contract: dict, expected: str) -> None:
        self.assertIn(expected, validate_contract(contract, self.deployment))

    def test_contract_and_iac_are_valid(self) -> None:
        self.assertEqual((), validate_contract(self.contract, self.deployment))
        self.assertEqual((), validate_iac_sources())
        self.assertRegex(canonical_digest(self.contract), r"^[0-9a-f]{64}$")

    def test_vke_freeze_cannot_be_promoted_or_retried(self) -> None:
        for field, value in (
            ("status", "PASSED"),
            ("targetClaim", "TARGET_PASS"),
            ("rootCauseClaim", "PROVIDER_FAILURE"),
            ("automaticV4Allowed", True),
            ("historicalAttemptsImmutable", False),
        ):
            with self.subTest(field=field):
                mutated = copy.deepcopy(self.contract)
                mutated["vkeDiagnosticFreeze"][field] = value
                self.assert_invalid(mutated, "vke_freeze")

    def test_region_and_authorization_are_fail_closed(self) -> None:
        for field, value in (
            ("region", "ewr"),
            ("resourceCreationAuthorized", True),
            ("spendAuthorized", True),
            ("liveMutationCallsAuthorized", True),
        ):
            with self.subTest(field=field):
                mutated = copy.deepcopy(self.contract)
                mutated["approvalBoundary"][field] = value
                self.assert_invalid(mutated, "approval_boundary")

    def test_vm_shape_cannot_expand_or_add_vke(self) -> None:
        mutated = copy.deepcopy(self.contract)
        mutated["infrastructure"]["resources"][0]["plan"] = "vc2-16c-64gb"
        self.assert_invalid(mutated, "infrastructure")

        mutated = copy.deepcopy(self.contract)
        mutated["infrastructure"]["vkeClusters"] = 1
        self.assert_invalid(mutated, "infrastructure")

    def test_public_exposure_cannot_widen(self) -> None:
        mutated = copy.deepcopy(self.contract)
        mutated["network"]["publicIngressRules"][0]["source"] = "0.0.0.0/0"
        self.assert_invalid(mutated, "network")

        mutated = copy.deepcopy(self.contract)
        mutated["network"]["publishedOtlpPorts"] = 2
        self.assert_invalid(mutated, "network")

    def test_vke_specific_items_remain_deferred(self) -> None:
        mutated = copy.deepcopy(self.contract)
        mutated["evidenceContractAudit"]["deferredVke"][0]["disposition"] = "PASSED"
        self.assert_invalid(mutated, "platform_audit")

        mutated = copy.deepcopy(self.contract)
        mutated["evidenceContractAudit"]["closureSemantics"][
            "vmEvidenceMayClaimVkeValidation"
        ] = True
        self.assert_invalid(mutated, "platform_audit")

    def test_mtls_and_queue_requirements_cannot_be_weakened(self) -> None:
        for field in (
            "applicationToGatewayMutualTls",
            "gatewayToBackendIngressMutualTls",
            "certificateSanValidationRequired",
        ):
            with self.subTest(field=field):
                mutated = copy.deepcopy(self.contract)
                mutated["telemetryTopology"]["tls"][field] = False
                self.assert_invalid(mutated, "telemetry_topology")

        mutated = copy.deepcopy(self.contract)
        mutated["telemetryTopology"]["gatewayPersistentQueue"] = False
        self.assert_invalid(mutated, "telemetry_topology")

        mutated = copy.deepcopy(self.contract)
        mutated["telemetryTopology"]["logSource"] = "mock logs"
        self.assert_invalid(mutated, "telemetry_topology")

    def test_cost_ceiling_and_quote_remain_bounded(self) -> None:
        mutated = copy.deepcopy(self.contract)
        mutated["cost"]["incrementalExecutionCeilingUsdCents"] = 301
        self.assert_invalid(mutated, "cost")

        mutated = copy.deepcopy(self.contract)
        mutated["cost"]["authenticatedQuoteRequiredBeforeProvision"] = False
        self.assert_invalid(mutated, "cost")

    def test_evidence_cannot_accept_mock_local_or_provider_docs(self) -> None:
        for field in (
            "mockEvidenceAccepted",
            "localComposeEvidenceAcceptedAsTarget",
            "providerDocumentationAcceptedAsRuntimeEvidence",
            "vmPassMayClaimVke",
            "externalPassMayClaimProductionDeployment",
        ):
            with self.subTest(field=field):
                mutated = copy.deepcopy(self.contract)
                mutated["evidenceContract"][field] = True
                self.assert_invalid(mutated, "evidence_contract")

    def test_secret_logging_and_production_data_are_forbidden(self) -> None:
        mutated = copy.deepcopy(self.contract)
        mutated["secretHandling"]["secretValueLoggingAllowed"] = True
        self.assert_invalid(mutated, "secret_handling")

    def test_backend_credentials_and_product_telemetry_controls_are_required(self) -> None:
        for field in (
            "metastoreCredentialGeneratedAtExecution",
            "clickHouseCredentialGeneratedAtExecution",
            "credentialsInjectedFromAclRestrictedSecretFiles",
            "foundryProductTelemetryDisabledOrEgressBlockedBeforeTargetForge",
            "deploymentMustFailIfCredentialOrTelemetryControlCannotBeVerified",
        ):
            with self.subTest(field=field):
                mutated = copy.deepcopy(self.contract)
                mutated["backendDecision"]["backendSecurity"][field] = False
                self.assert_invalid(mutated, "backend")

        mutated = copy.deepcopy(self.contract)
        mutated["backendDecision"]["backendSecurity"]["directBackendPortsPublished"] = True
        self.assert_invalid(mutated, "backend")

        for field in (
            "signozAnalyticsEnabled",
            "signozStatsReporterEnabled",
            "signozStatsReporterIdentityCollectionEnabled",
        ):
            with self.subTest(field=field):
                mutated = copy.deepcopy(self.contract)
                mutated["backendDecision"]["backendSecurity"][field] = True
                self.assert_invalid(mutated, "backend")

        mutated = copy.deepcopy(self.contract)
        mutated["backendDecision"]["backendSecurity"]["foundryInvocationRequiredFlags"] = ["--no-ledger"]
        self.assert_invalid(mutated, "backend")

        mutated = copy.deepcopy(self.contract)
        mutated["workload"]["productionDataAllowed"] = True
        self.assert_invalid(mutated, "workload")

    def test_r3_325_remains_frozen(self) -> None:
        mutated = copy.deepcopy(self.contract)
        mutated["scientificBoundary"]["frozenR3_325"] = (
            "E-PASS / X-PASS / S-PASS / C-PASS"
        )
        self.assert_invalid(mutated, "scientific_boundary")

    def test_iac_rejects_extra_resource_and_public_ports(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            for source in IAC_ROOT.iterdir():
                if source.is_file():
                    (target / source.name).write_bytes(source.read_bytes())
            main = target / "main.tf"
            main.write_text(
                main.read_text(encoding="utf-8")
                + '\nresource "vultr_kubernetes" "forbidden" {}\n',
                encoding="utf-8",
            )
            findings = validate_iac_sources(target)
            self.assertTrue(any(item.startswith("terraform_") for item in findings))

        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            for source in IAC_ROOT.iterdir():
                if source.is_file():
                    (target / source.name).write_bytes(source.read_bytes())
            compose = target / "routemind-compose.yaml"
            compose.write_text(
                compose.read_text(encoding="utf-8")
                + "\n# forbidden mutation\n  ports:\n    - '8080:8080'\n",
                encoding="utf-8",
            )
            self.assertIn("compose_host_ports", validate_iac_sources(target))

        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            for source in IAC_ROOT.iterdir():
                if source.is_file():
                    (target / source.name).write_bytes(source.read_bytes())
            gateway = target / "gateway-collector.yaml"
            gateway.write_text(
                gateway.read_text(encoding="utf-8").replace(
                    "filelog/business", "filelog/removed"
                ),
                encoding="utf-8",
            )
            self.assertIn("gateway_log_export", validate_iac_sources(target))

    def test_contract_file_is_canonical_json_object(self) -> None:
        value = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        self.assertIsInstance(value, dict)
        self.assertEqual(self.contract, value)


if __name__ == "__main__":
    unittest.main()
