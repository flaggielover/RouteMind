from __future__ import annotations

import copy
import unittest

import deployment_contract as contract


class DeploymentContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.payload = contract.load_json(contract.CONTRACT_PATH)
        self.catalog = contract.load_json(contract.CATALOG_PATH)
        self.catalog_sha256 = contract.sha256_file(contract.CATALOG_PATH)

    def assert_rejected(self, mutate, expected: str) -> None:  # type: ignore[no-untyped-def]
        candidate = copy.deepcopy(self.payload)
        evidence = copy.deepcopy(self.catalog)
        mutate(candidate, evidence)
        self.assertIn(
            expected,
            contract.validate_contract(candidate, evidence, self.catalog_sha256),
        )

    def test_frozen_contract_is_valid_and_deterministic(self) -> None:
        self.assertEqual(
            contract.validate_contract(self.payload, self.catalog, self.catalog_sha256),
            [],
        )
        self.assertEqual(contract.digest(self.payload), contract.digest(copy.deepcopy(self.payload)))

    def test_target_cannot_move_outside_vultr_tokyo(self) -> None:
        self.assert_rejected(
            lambda value, _catalog: value["target"].update(regionId="itm", city="Osaka"),
            "target:region",
        )

    def test_catalog_must_prove_required_tokyo_capabilities(self) -> None:
        self.assert_rejected(
            lambda _value, catalog: catalog["region"]["options"].remove("kubernetes"),
            "catalog:region",
        )

    def test_resource_spend_and_deployment_remain_unauthorized(self) -> None:
        self.assert_rejected(
            lambda value, _catalog: value["approval"].update(resourceCreationAuthorized=True),
            "approval:resourceCreationAuthorized",
        )
        self.assert_rejected(
            lambda value, _catalog: value["approval"].update(spendAuthorized=True),
            "approval:spendAuthorized",
        )
        self.assert_rejected(
            lambda value, _catalog: value["target"].update(productionVerified=True),
            "target:false_deployment_claim",
        )

    def test_java_and_postgresql_authority_cannot_drift(self) -> None:
        self.assert_rejected(
            lambda value, _catalog: value["ownership"].update(durableBusinessState="Python compute API"),
            "ownership:java_authority",
        )
        self.assert_rejected(
            lambda value, _catalog: next(item for item in value["topology"]["services"] if item["id"] == "redis").update(durableAuthority=True),
            "topology:authority_leak",
        )

    def test_single_region_failure_must_remain_explicit(self) -> None:
        self.assert_rejected(
            lambda value, _catalog: next(item for item in value["failureDomains"] if item["id"] == "tokyo_region").update(mitigation="multi-region failover"),
            "failure_domain:single_region",
        )

    def test_data_residency_and_backup_boundary_cannot_weaken(self) -> None:
        self.assert_rejected(
            lambda value, _catalog: value["dataResidency"].update(boundary="Asia Pacific"),
            "residency:boundary",
        )
        self.assert_rejected(
            lambda value, _catalog: value["dataResidency"].update(providerAutomaticBackups="enabled"),
            "residency:provider_backups",
        )

    def test_capacity_baseline_cannot_be_promoted_to_production(self) -> None:
        self.assert_rejected(
            lambda value, _catalog: value["capacityAssumptions"]["baselineEvidence"].update(scope="production_capacity"),
            "capacity:baseline_scope",
        )

    def test_slos_and_recovery_targets_are_complete(self) -> None:
        self.assert_rejected(
            lambda value, _catalog: value["serviceLevelObjectives"].pop(),
            "slo:coverage",
        )
        self.assert_rejected(
            lambda value, _catalog: next(item for item in value["serviceLevelObjectives"] if item["id"] == "api-availability").update(errorBudgetMinutes=0),
            "slo:availability",
        )

    def test_cost_arithmetic_catalog_and_ceiling_are_frozen(self) -> None:
        self.assert_rejected(
            lambda value, _catalog: next(item for item in value["costModel"]["recurringItems"] if item["id"] == "vke-worker-nodes").update(monthlyUsdCents=1),
            "cost:arithmetic:vke-worker-nodes",
        )
        self.assert_rejected(
            lambda value, _catalog: value["costModel"].update(planningCeilingMonthlyUsdCents=23900),
            "cost:ceiling",
        )

    def test_catalog_digest_and_round3_boundary_are_immutable(self) -> None:
        self.assert_rejected(
            lambda value, _catalog: value["evidence"].update(catalogSha256="0" * 64),
            "evidence:catalog_digest",
        )
        self.assert_rejected(
            lambda value, _catalog: value["scientificBoundary"].update(frozenR3_325="S-PASS / C-PASS"),
            "science:frozen_boundary",
        )


if __name__ == "__main__":
    unittest.main()
