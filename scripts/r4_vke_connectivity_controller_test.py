from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class VkeConnectivityControllerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.controller = (ROOT / "scripts" / "r4_vke_connectivity_diagnostic.ps1").read_text(
            encoding="utf-8"
        )
        cls.iac = (
            ROOT
            / "infra"
            / "external-validation"
            / "vultr-tokyo-diagnostic"
            / "main.tf"
        ).read_text(encoding="utf-8")

    def test_controller_requires_exact_digest_and_clean_tracked_tree(self) -> None:
        self.assertIn("ROUTEMIND_EXTERNAL_EXECUTION_APPROVAL_DIGEST", self.controller)
        self.assertIn('"status"', self.controller)
        self.assertIn("HEAD == origin/main", self.controller)

    def test_controller_validates_plan_before_apply_and_tears_down(self) -> None:
        self.assertIn("$PlanScript, $planJson", self.controller)
        self.assertIn("finally", self.controller)
        self.assertIn("Invoke-Teardown", self.controller)

    def test_controller_never_allows_broad_firewall_or_public_ingress(self) -> None:
        self.assertIn("subnet_size -ne 32", self.controller)
        self.assertNotIn("0.0.0.0/0", self.controller)
        self.assertNotIn("::/0", self.controller)
        self.assertNotIn("helm", self.controller.lower())
        self.assertNotIn("kubectl apply", self.controller.lower())

    def test_iac_has_two_observer_rules_and_no_storage_or_load_balancer(self) -> None:
        self.assertEqual(self.iac.count('port              = "6443"'), 2)
        self.assertEqual(self.iac.count("subnet_size       = 32"), 3)
        self.assertIn("vultr_instance.recovery.main_ip", self.iac)
        self.assertNotIn("vultr_load_balancer", self.iac)
        self.assertNotIn("vultr_block_storage", self.iac)


if __name__ == "__main__":
    unittest.main()
