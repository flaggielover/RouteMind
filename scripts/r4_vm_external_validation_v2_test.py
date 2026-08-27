from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from r4_vm_external_validation import validate_iac_sources as validate_runtime_sources
from r4_vm_external_validation_v2 import (
    CONTRACT_PATH,
    DEPLOYMENT_CONTRACT_PATH,
    IAC_ROOT,
    RUNTIME_ROOT,
    canonical_digest,
    load_object,
    validate_contract,
    validate_iac_sources,
)


class VmExternalValidationV2ContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = load_object(CONTRACT_PATH)
        self.deployment = load_object(DEPLOYMENT_CONTRACT_PATH)

    def assert_invalid(self, contract: dict, expected: str) -> None:
        self.assertIn(expected, validate_contract(contract, self.deployment))

    def copy_iac(self, target: Path) -> None:
        for source in IAC_ROOT.iterdir():
            if source.is_file():
                (target / source.name).write_bytes(source.read_bytes())

    def test_contract_iac_and_shared_runtime_are_valid(self) -> None:
        self.assertEqual((), validate_contract(self.contract, self.deployment))
        self.assertEqual((), validate_iac_sources())
        self.assertEqual((), validate_runtime_sources(RUNTIME_ROOT))
        self.assertRegex(canonical_digest(self.contract), r"^[0-9a-f]{64}$")

    def test_consumed_v1_digest_cannot_be_reused_or_reinterpreted(self) -> None:
        for field, value in (
            ("digestConsumed", False),
            ("reusable", True),
            ("result", "PASSED"),
            ("canonicalSha256", "0" * 64),
        ):
            with self.subTest(field=field):
                mutated = copy.deepcopy(self.contract)
                mutated["predecessor"][field] = value
                self.assert_invalid(mutated, "predecessor")

    def test_quota_audit_remains_read_only_and_existing_vpcs_are_not_reused(self) -> None:
        for field, value in (
            ("providerMutationPerformed", True),
            ("existingVpcReuseProvenSafe", True),
            ("unusedInferenceAllowed", True),
            ("selectedTopology", "EXISTING_VPC"),
            ("vpcReuseCount", 1),
        ):
            with self.subTest(field=field):
                mutated = copy.deepcopy(self.contract)
                mutated["quotaResolution"][field] = value
                self.assert_invalid(mutated, "quota_resolution")

    def test_vpc_create_count_and_vm_shapes_cannot_drift(self) -> None:
        mutated = copy.deepcopy(self.contract)
        mutated["infrastructure"]["vpcCreateCount"] = 1
        self.assert_invalid(mutated, "infrastructure")

        mutated = copy.deepcopy(self.contract)
        mutated["infrastructure"]["resources"][0]["plan"] = "vc2-16c-64gb"
        self.assert_invalid(mutated, "infrastructure")

        mutated = copy.deepcopy(self.contract)
        mutated["infrastructure"]["terraformResourceCounts"]["vultr_instance"] = 3
        self.assert_invalid(mutated, "infrastructure")

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

    def test_public_ingress_is_exactly_operator_and_recovery_ssh_32(self) -> None:
        mutated = copy.deepcopy(self.contract)
        mutated["network"]["publicIngressRules"][0]["source"] = "0.0.0.0/0"
        self.assert_invalid(mutated, "network")

        mutated = copy.deepcopy(self.contract)
        mutated["network"]["publicIngressRules"][1]["subnetSize"] = 24
        self.assert_invalid(mutated, "network")

        mutated = copy.deepcopy(self.contract)
        mutated["network"]["publicIngressRules"].append(
            {"id": "database", "protocol": "tcp", "port": 5432, "source": "0.0.0.0/0"}
        )
        self.assert_invalid(mutated, "network")

    def test_internal_services_and_telemetry_cannot_be_published(self) -> None:
        for field in (
            "publishedApplicationPorts",
            "publishedDatabasePorts",
            "publishedMessagingPorts",
            "publishedCachePorts",
            "publishedOtlpPorts",
            "publishedCollectorHealthPorts",
            "publishedBackendPorts",
        ):
            with self.subTest(field=field):
                mutated = copy.deepcopy(self.contract)
                mutated["network"][field] = 1
                self.assert_invalid(mutated, "network")

    def test_inter_vm_transfer_requires_identity_encryption_and_host_key_pin(self) -> None:
        for field in (
            "sourceRuleCreatedOnlyAfterRecoveryIdentityExists",
            "publicKeyAuthenticationOnly",
            "strictHostKeyCheckingRequired",
            "hostKeyFingerprintPersistedBeforeTransfer",
            "payloadEncryptedBeforeTransfer",
            "payloadSha256Bound",
        ):
            with self.subTest(field=field):
                mutated = copy.deepcopy(self.contract)
                mutated["interVmSecurity"][field] = False
                self.assert_invalid(mutated, "inter_vm_security")

        for field in (
            "passwordAuthenticationAllowed",
            "rawPayloadMayTransitOperatorMachine",
            "plaintextServiceTrafficBetweenVmsAllowed",
        ):
            with self.subTest(field=field):
                mutated = copy.deepcopy(self.contract)
                mutated["interVmSecurity"][field] = True
                self.assert_invalid(mutated, "inter_vm_security")

    def test_vke_freeze_and_property_classification_cannot_be_promoted(self) -> None:
        mutated = copy.deepcopy(self.contract)
        mutated["vkeDiagnosticFreeze"]["targetClaim"] = "TARGET_PASS"
        self.assert_invalid(mutated, "vke_freeze")

        mutated = copy.deepcopy(self.contract)
        mutated["evidenceContractAudit"]["propertyClassification"]["newVpc"] = (
            "REQUIRED_PROPERTY"
        )
        self.assert_invalid(mutated, "property_audit")

        mutated = copy.deepcopy(self.contract)
        mutated["evidenceContractAudit"]["deferredVke"][0]["disposition"] = "PASSED"
        self.assert_invalid(mutated, "property_audit")

    def test_evidence_cannot_accept_mock_local_provider_or_production_claims(self) -> None:
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

    def test_cost_and_secret_boundaries_cannot_be_weakened(self) -> None:
        mutated = copy.deepcopy(self.contract)
        mutated["cost"]["incrementalExecutionCeilingUsdCents"] = 301
        self.assert_invalid(mutated, "cost")

        mutated = copy.deepcopy(self.contract)
        mutated["cost"]["authenticatedQuoteRequiredBeforeProvision"] = False
        self.assert_invalid(mutated, "cost")

        mutated = copy.deepcopy(self.contract)
        mutated["secretHandling"]["secretValueLoggingAllowed"] = True
        self.assert_invalid(mutated, "secret_handling")

    def test_teardown_never_owns_or_deletes_a_vpc(self) -> None:
        mutated = copy.deepcopy(self.contract)
        mutated["automation"]["vpcDeleteAllowed"] = True
        self.assert_invalid(mutated, "automation")

        mutated = copy.deepcopy(self.contract)
        mutated["automation"]["ownedProviderResourceTypes"].append("vultr_vpc")
        self.assert_invalid(mutated, "automation")

        mutated = copy.deepcopy(self.contract)
        mutated["automation"]["applyMayUseOnlyValidatedSavedPlan"] = False
        self.assert_invalid(mutated, "automation")

    def test_r3_325_remains_frozen(self) -> None:
        mutated = copy.deepcopy(self.contract)
        mutated["scientificBoundary"]["frozenR3_325"] = (
            "E-PASS / X-PASS / S-PASS / C-PASS"
        )
        self.assert_invalid(mutated, "scientific_boundary")

    def test_iac_rejects_vpc_wide_cidr_vpc_attachment_and_wrong_source(self) -> None:
        mutations = (
            ('\nresource "vultr_vpc" "forbidden" {}\n', "terraform_resource_inventory"),
            ('\n# subnet = "0.0.0.0"\n', 'terraform_forbidden:subnet = "0.0.0.0"'),
            ("\nvpc_ids = [\"forbidden\"]\n", "terraform_vpc_attachment"),
        )
        for addition, expected in mutations:
            with self.subTest(expected=expected), tempfile.TemporaryDirectory() as directory:
                target = Path(directory)
                self.copy_iac(target)
                main = target / "main.tf"
                main.write_text(main.read_text(encoding="utf-8") + addition, encoding="utf-8")
                self.assertIn(expected, validate_iac_sources(target))

        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            self.copy_iac(target)
            main = target / "main.tf"
            main.write_text(
                main.read_text(encoding="utf-8").replace(
                    "subnet            = vultr_instance.recovery.main_ip",
                    "subnet            = local.operator_ipv4",
                ),
                encoding="utf-8",
            )
            self.assertIn(
                "terraform_missing_boundary:recovery_source", validate_iac_sources(target)
            )

    def test_iac_requires_ssh_password_auth_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            self.copy_iac(target)
            cloud_init = target / "cloud-init.yaml.tftpl"
            cloud_init.write_text(
                cloud_init.read_text(encoding="utf-8").replace(
                    "ssh_pwauth: false", "ssh_pwauth: true"
                ),
                encoding="utf-8",
            )
            self.assertIn("cloud_init_password_auth", validate_iac_sources(target))

    def test_contract_file_is_canonical_json_object(self) -> None:
        value = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        self.assertIsInstance(value, dict)
        self.assertEqual(self.contract, value)


if __name__ == "__main__":
    unittest.main()
