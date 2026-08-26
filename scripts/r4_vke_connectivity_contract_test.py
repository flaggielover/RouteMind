from __future__ import annotations

import copy
import unittest

import r4_vke_connectivity_contract as contract


class VkeConnectivityContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.value = contract.load_contract()

    def test_v2_contract_passes_and_has_new_digest(self) -> None:
        self.assertEqual(contract.validate(self.value), ())
        self.assertNotEqual(contract.canonical_digest(self.value), contract.OLD_CONTRACT_DIGEST)

    def test_old_digest_cannot_be_reused(self) -> None:
        candidate = copy.deepcopy(self.value)
        candidate["supersedesContractDigest"] = (
            "c2a1695104ba7297b51b1c949fa689a4efeb5974dcf1a2122c12f91a57f4e2df"
        )
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


if __name__ == "__main__":
    unittest.main()
