from __future__ import annotations

import copy
import unittest

import r4_vke_connectivity_plan as plan


def valid_plan(action: str = "create") -> dict:
    return {
        "resource_changes": [
            {
                "address": address,
                "type": resource_type,
                "change": {"actions": [action]},
            }
            for address, resource_type in (
                ("vultr_firewall_group.recovery", "vultr_firewall_group"),
                ("vultr_firewall_rule.recovery_ssh", "vultr_firewall_rule"),
                ("vultr_firewall_rule.vke_api_operator", "vultr_firewall_rule"),
                ("vultr_firewall_rule.vke_api_recovery", "vultr_firewall_rule"),
                ("vultr_instance.recovery", "vultr_instance"),
                ("vultr_kubernetes.diagnostic", "vultr_kubernetes"),
            )
        ]
    }


class DiagnosticPlanTests(unittest.TestCase):
    def test_exact_create_inventory_passes(self) -> None:
        self.assertEqual(plan.validate_plan(valid_plan()), ())

    def test_exact_destroy_inventory_passes(self) -> None:
        self.assertEqual(plan.validate_plan(valid_plan("delete"), destroy=True), ())

    def test_extra_load_balancer_is_rejected(self) -> None:
        candidate = copy.deepcopy(valid_plan())
        candidate["resource_changes"].append(
            {
                "address": "vultr_load_balancer.forbidden",
                "type": "vultr_load_balancer",
                "change": {"actions": ["create"]},
            }
        )
        self.assertIn("resource_type:vultr_load_balancer", plan.validate_plan(candidate))

    def test_missing_observer_rule_is_rejected(self) -> None:
        candidate = valid_plan()
        candidate["resource_changes"] = candidate["resource_changes"][:-1]
        findings = plan.validate_plan(candidate)
        self.assertIn("resource_inventory", findings)
        self.assertIn("resource_addresses", findings)


if __name__ == "__main__":
    unittest.main()
