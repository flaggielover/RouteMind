from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

import r4_vke_connectivity_contract as contract


class VkeConnectivityContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.value = contract.load_contract()

    def test_v3_contract_passes_and_has_new_digest(self) -> None:
        self.assertEqual(contract.validate(self.value), ())
        self.assertNotEqual(contract.canonical_digest(self.value), contract.V2_CONTRACT_DIGEST)

    def test_v1_and_v2_contract_files_remain_immutable(self) -> None:
        root = Path(__file__).resolve().parents[1] / "contracts" / "external-validation"
        v1 = json.loads((root / "r4-vultr-tokyo-vke-connectivity-diagnostic-v1.json").read_text(encoding="utf-8"))
        v2 = json.loads((root / "r4-vultr-tokyo-vke-connectivity-diagnostic-v2.json").read_text(encoding="utf-8"))
        self.assertEqual(contract.canonical_digest(v2), contract.V2_CONTRACT_DIGEST)
        self.assertEqual(v1["contractId"], "r4-vultr-tokyo-vke-connectivity-diagnostic-v1")
        self.assertEqual(v2["contractId"], "r4-vultr-tokyo-vke-connectivity-diagnostic-v2")

    def test_old_digest_cannot_be_reused(self) -> None:
        candidate = copy.deepcopy(self.value)
        candidate["supersedesContractDigest"] = contract.V1_CONTRACT_DIGEST
        self.assertIn("identity", contract.validate(candidate))

    def test_prior_incomplete_outcome_cannot_be_reinterpreted(self) -> None:
        candidate = copy.deepcopy(self.value)
        candidate["priorExecution"]["classification"] = "BOTH_OBSERVERS_FAILED"
        self.assertIn("prior_execution", contract.validate(candidate))

    def test_resource_or_firewall_expansion_is_rejected(self) -> None:
        resource_candidate = copy.deepcopy(self.value)
        resource_candidate["infrastructure"]["resources"].append(
            {"id": "forbidden-load-balancer", "type": "Load Balancer"}
        )
        self.assertIn("resources", contract.validate(resource_candidate))
        firewall_candidate = copy.deepcopy(self.value)
        firewall_candidate["infrastructure"]["firewallRules"][0]["subnetSize"] = 0
        self.assertIn("firewall_rule_shape", contract.validate(firewall_candidate))

    def test_scientific_boundary_is_immutable(self) -> None:
        candidate = copy.deepcopy(self.value)
        candidate["scientificBoundary"]["frozenR3_325"] = "E-PASS / X-PASS / S-PASS / C-PASS"
        self.assertIn("scientific_boundary", contract.validate(candidate))

    def test_independent_artifact_and_failure_contract_is_required(self) -> None:
        candidate = copy.deepcopy(self.value)
        candidate["observerIsolation"]["oneSideFailureCannotPreventOther"] = False
        self.assertIn("observer_isolation", contract.validate(candidate))
        candidate = copy.deepcopy(self.value)
        candidate["failureInjection"] = ["operator_execution_fails"]
        self.assertIn("failure_injection", contract.validate(candidate))


if __name__ == "__main__":
    unittest.main()
