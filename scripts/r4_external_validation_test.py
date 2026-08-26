from __future__ import annotations

import copy
import unittest
from datetime import UTC, datetime, timedelta
from typing import Any

import r4_external_validation as external


def timestamp(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def valid_evidence(contract: dict[str, Any]) -> dict[str, Any]:
    started = datetime(2026, 8, 25, 12, 0, tzinfo=UTC)
    completed = started + timedelta(hours=2)
    artifact_ids = sorted(external.EXPECTED_ARTIFACTS)
    report: dict[str, Any] = {
        "schemaVersion": "r4-external-validation-evidence.v1",
        "evidenceId": "fixture-not-runtime-evidence",
        "contractDigest": external.canonical_digest(contract),
        "classification": "EXTERNAL_VALIDATION_PASS",
        "productionDeploymentVerified": False,
        "execution": {
            "id": "r4-ext-20260825t120000z-abcdef0",
            "startedAt": timestamp(started),
            "completedAt": timestamp(completed),
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
        "resources": [
            {
                "type": resource_type,
                "providerId": f"fixture-{index}",
                "region": "nrt",
                "createdAt": timestamp(started),
                "deletedAt": timestamp(completed),
                "cleanupVerified": True,
            }
            for index, resource_type in enumerate(sorted(external.EXPECTED_RESOURCE_TYPES))
        ],
        "checks": {
            name: {
                "status": "PASS",
                "observedAt": timestamp(completed),
                "artifactIds": [artifact_ids[index % len(artifact_ids)]],
            }
            for index, name in enumerate(contract["evidenceContract"]["requiredChecks"])
        },
        "correlation": {
            "traceId": "a" * 32,
            "boundaries": sorted(external.EXPECTED_BOUNDARIES),
            "singleTrace": False,
            "actualRouteMindWorkload": True,
            "syntheticQualificationTraffic": True,
        },
        "tenantBoundary": {
            "rawIdentifierFindings": 0,
            "pseudonymizedKeysOnly": True,
            "maximumObservedActiveKeys": 4,
        },
        "leakage": {
            "secretFindings": 0,
            "rawTenantIdentifierFindings": 0,
            "productionDataFindings": 0,
            "scanCompleted": True,
        },
        "resourceUsage": {
            "peakCpuCores": 5.5,
            "peakMemoryMiB": 9216,
            "peakStorageGiB": 44,
        },
        "cost": {
            "currency": "USD",
            "source": "authenticated_vultr_quote_and_runtime_bound",
            "upperBoundUsdCents": 480,
            "withinApprovedCeiling": True,
        },
        "artifacts": [
            {
                "id": artifact_id,
                "path": f"evidence/external/R4-405/{artifact_id}.json",
                "sha256": character * 64,
                "byteSize": index + 1,
                "capturedAt": timestamp(completed),
                "containsSecrets": False,
            }
            for index, (artifact_id, character) in enumerate(
                zip(artifact_ids, "abcdef1234567", strict=True)
            )
        ],
        "cleanup": {
            "complete": True,
            "credentialedInventoryCheck": True,
            "remainingResourceIds": [],
            "localPrivateKeysDeleted": True,
            "kubeconfigDeleted": True,
            "verifiedAt": timestamp(completed),
        },
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
    report["reportDigest"] = external.canonical_digest(report)
    return report


def mutate_report(report: dict[str, Any], change) -> dict[str, Any]:  # type: ignore[no-untyped-def]
    candidate = copy.deepcopy(report)
    change(candidate)
    candidate["reportDigest"] = external.canonical_digest(
        candidate, omit="reportDigest"
    )
    return candidate


class ExternalValidationPreparationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = external.load_object(external.CONTRACT_PATH)
        cls.deployment = external.load_object(external.DEPLOYMENT_CONTRACT_PATH)

    def test_preparation_contract_is_valid_and_still_not_authorized(self) -> None:
        self.assertEqual(external.validate_contract(self.contract, self.deployment), ())
        self.assertFalse(self.contract["approvalBoundary"]["resourceCreationAuthorized"])
        self.assertFalse(self.contract["approvalBoundary"]["spendAuthorized"])
        self.assertFalse(self.contract["scope"]["externalValidationExecuted"])

    def test_backend_selection_and_tokyo_boundary_cannot_drift(self) -> None:
        candidate = copy.deepcopy(self.contract)
        candidate["backendDecision"]["selected"] = "grafana-otel-lgtm"
        self.assertIn(
            "backend_decision",
            external.validate_contract(candidate, self.deployment),
        )
        candidate = copy.deepcopy(self.contract)
        candidate["approvalBoundary"]["region"] = "ewr"
        self.assertIn(
            "approval_boundary",
            external.validate_contract(candidate, self.deployment),
        )
        candidate = copy.deepcopy(self.contract)
        candidate["infrastructure"]["resourceLimits"][
            "persistentVolumeClaimCountMaximum"
        ] = 4
        self.assertIn(
            "infrastructure",
            external.validate_contract(candidate, self.deployment),
        )
        candidate = copy.deepcopy(self.contract)
        kubernetes_boundary = next(
            item
            for item in candidate["telemetryTopology"]["networkBoundaries"]
            if item["id"] == "provider-kubernetes-control-plane"
        )
        kubernetes_boundary["port"] = 443
        self.assertIn(
            "telemetry_topology",
            external.validate_contract(candidate, self.deployment),
        )
        candidate = copy.deepcopy(self.contract)
        vke = next(
            item
            for item in candidate["infrastructure"]["resources"]
            if item["id"] == "validation-vke"
        )
        vke["controlPlaneFirewall"]["subnetSizeRequired"] = 24
        self.assertIn(
            "infrastructure",
            external.validate_contract(candidate, self.deployment),
        )

    def test_secret_cost_and_science_gates_cannot_weaken(self) -> None:
        candidate = copy.deepcopy(self.contract)
        candidate["secretHandling"]["secretValueLoggingAllowed"] = True
        self.assertIn(
            "secret_handling",
            external.validate_contract(candidate, self.deployment),
        )
        candidate = copy.deepcopy(self.contract)
        candidate["cost"]["executionAuthorizationCeilingUsdCents"] = 50000
        self.assertIn(
            "cost_boundary", external.validate_contract(candidate, self.deployment)
        )
        candidate = copy.deepcopy(self.contract)
        candidate["scientificBoundary"]["frozenR3_325"] = (
            "E-PASS / X-PASS / S-PASS / C-PASS"
        )
        self.assertIn(
            "scientific_boundary",
            external.validate_contract(candidate, self.deployment),
        )

    def test_complete_live_evidence_shape_passes(self) -> None:
        report = valid_evidence(self.contract)
        self.assertEqual(external.validate_evidence(report, self.contract), ())

    def test_mock_local_or_production_claims_are_rejected(self) -> None:
        report = valid_evidence(self.contract)
        mock = mutate_report(
            report, lambda value: value["execution"].update(mockEvidence=True)
        )
        compose = mutate_report(
            report,
            lambda value: value["execution"].update(composeEvidencePromoted=True),
        )
        production = mutate_report(
            report, lambda value: value.update(productionDeploymentVerified=True)
        )
        self.assertIn("execution", external.validate_evidence(mock, self.contract))
        self.assertIn("execution", external.validate_evidence(compose, self.contract))
        self.assertIn("identity", external.validate_evidence(production, self.contract))

    def test_missing_signal_leakage_cost_or_cleanup_evidence_is_rejected(self) -> None:
        report = valid_evidence(self.contract)
        missing_log = mutate_report(
            report, lambda value: value["checks"].pop("log_correlation")
        )
        leakage = mutate_report(
            report,
            lambda value: value["leakage"].update(rawTenantIdentifierFindings=1),
        )
        cost = mutate_report(
            report, lambda value: value["cost"].update(upperBoundUsdCents=1501)
        )
        cleanup = mutate_report(
            report,
            lambda value: value["cleanup"].update(remainingResourceIds=["leftover"]),
        )
        self.assertIn("check_set", external.validate_evidence(missing_log, self.contract))
        self.assertIn(
            "tenant_or_leakage", external.validate_evidence(leakage, self.contract)
        )
        self.assertIn("cost", external.validate_evidence(cost, self.contract))
        self.assertIn("cleanup", external.validate_evidence(cleanup, self.contract))

    def test_stale_digest_or_round3_promotion_is_rejected(self) -> None:
        report = valid_evidence(self.contract)
        stale = copy.deepcopy(report)
        stale["cost"]["upperBoundUsdCents"] = 1
        promoted = mutate_report(
            report,
            lambda value: value["scientificBoundary"].update(
                frozenR3_325="E-PASS / X-PASS / S-PASS / C-PASS"
            ),
        )
        self.assertIn("report_digest", external.validate_evidence(stale, self.contract))
        self.assertIn(
            "scientific_boundary",
            external.validate_evidence(promoted, self.contract),
        )

    def test_terraform_apply_and_destroy_plans_are_exact(self) -> None:
        def plan(action: str) -> dict[str, Any]:
            return {
                "resource_changes": [
                    {
                        "address": f"{resource_type}.fixture",
                        "type": resource_type,
                        "change": {"actions": [action]},
                    }
                    for resource_type, count in external.EXPECTED_TERRAFORM_TYPES.items()
                    for index in range(count)
                ]
            }

        self.assertEqual(external.validate_terraform_plan(plan("create")), ())
        self.assertEqual(
            external.validate_terraform_plan(plan("delete"), destroy=True), ()
        )
        partial_destroy = plan("delete")
        partial_destroy["resource_changes"] = partial_destroy["resource_changes"][:2]
        self.assertEqual(
            external.validate_terraform_plan(
                partial_destroy, destroy=True, allow_partial_destroy=True
            ),
            (),
        )
        expanded = plan("create")
        expanded["resource_changes"].append(
            {
                "address": "vultr_load_balancer.forbidden",
                "type": "vultr_load_balancer",
                "change": {"actions": ["create"]},
            }
        )
        self.assertIn(
            "resource_type:vultr_load_balancer",
            external.validate_terraform_plan(expanded),
        )


if __name__ == "__main__":
    unittest.main()
