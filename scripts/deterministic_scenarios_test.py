from __future__ import annotations

import unittest

import deterministic_scenarios as scenarios


class DeterministicScenarioTests(unittest.TestCase):
    def setUp(self) -> None:
        self.catalog = scenarios.load_catalog()

    def test_catalog_is_finite_and_frozen(self) -> None:
        self.assertEqual(
            tuple(item["id"] for item in self.catalog["scenarios"]),
            scenarios.EXPECTED_IDS,
        )
        self.assertEqual(self.catalog["source"], "SIMULATION")
        self.assertIn("not a causal production claim", self.catalog["claim_label"])

    def test_same_manifest_has_same_digest(self) -> None:
        record = self.catalog["scenarios"][0]
        first = scenarios.run_scenario(record, 17)
        second = scenarios.run_scenario(record, 17)
        self.assertEqual(first["replay_digest"], second["replay_digest"])
        self.assertTrue(first["replay_verified"])

    def test_representative_supported_behaviors(self) -> None:
        results = {
            record["id"]: scenarios.run_scenario(record, 17)
            for record in self.catalog["scenarios"]
        }
        self.assertGreater(
            results["DINNER_RUSH"]["decision_count"],
            results["NORMAL_BASELINE"]["decision_count"],
        )
        self.assertGreater(results["COURIER_SHORTAGE"]["unassigned_count"], 0)
        self.assertTrue(results["ROUTING_PROVIDER_FAILURE"]["replay_verified"])
        self.assertTrue(results["RECOVERY"]["recovery_replay_verified"])

    def test_unknown_scenario_is_rejected_by_argparse(self) -> None:
        with self.assertRaises(SystemExit):
            scenarios.main(["--scenario", "UNKNOWN"])


if __name__ == "__main__":
    unittest.main()
