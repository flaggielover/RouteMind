from __future__ import annotations

import copy
import unittest

import r4_vm_external_plan_v2 as plan


def valid_plan(action: str = "create") -> dict:
    resources = (
        ("vultr_firewall_group.validation", "vultr_firewall_group", {}),
        (
            "vultr_firewall_rule.operator_ssh",
            "vultr_firewall_rule",
            {"protocol": "tcp", "ip_type": "v4", "port": "22", "subnet_size": 32, "subnet": "203.0.113.7"},
        ),
        (
            "vultr_firewall_rule.recovery_to_primary_ssh",
            "vultr_firewall_rule",
            {"protocol": "tcp", "ip_type": "v4", "port": "22", "subnet_size": 32, "subnet": None},
        ),
        (
            "vultr_instance.primary",
            "vultr_instance",
            {"plan": "vc2-8c-32gb", "region": "nrt", "backups": "disabled", "enable_ipv6": False, "ddos_protection": False, "activation_email": False, "vpc_ids": None},
        ),
        (
            "vultr_instance.recovery",
            "vultr_instance",
            {"plan": "vc2-2c-4gb", "region": "nrt", "backups": "disabled", "enable_ipv6": False, "ddos_protection": False, "activation_email": False, "vpc_ids": []},
        ),
    )
    return {
        "resource_changes": [
            {
                "address": address,
                "type": resource_type,
                "change": {
                    "actions": [action],
                    "after": after,
                    "after_unknown": {"subnet": True}
                    if address == "vultr_firewall_rule.recovery_to_primary_ssh"
                    else {},
                },
            }
            for address, resource_type, after in resources
        ]
    }


class VmExternalPlanV2Tests(unittest.TestCase):
    def test_exact_create_inventory_passes(self) -> None:
        self.assertEqual((), plan.validate_plan(valid_plan()))

    def test_exact_destroy_inventory_passes(self) -> None:
        self.assertEqual((), plan.validate_plan(valid_plan("delete"), destroy=True))

    def test_vpc_and_extra_instance_are_rejected(self) -> None:
        candidate = copy.deepcopy(valid_plan())
        candidate["resource_changes"].append(
            {
                "address": "vultr_vpc.forbidden",
                "type": "vultr_vpc",
                "change": {"actions": ["create"], "after": {}, "after_unknown": {}},
            }
        )
        findings = plan.validate_plan(candidate)
        self.assertIn("resource_type:vultr_vpc", findings)
        self.assertIn("resource_inventory", findings)

    def test_wide_ssh_rule_is_rejected(self) -> None:
        candidate = copy.deepcopy(valid_plan())
        change = candidate["resource_changes"][1]["change"]
        change["after"]["subnet"] = "0.0.0.0"
        change["after"]["subnet_size"] = 0
        findings = plan.validate_plan(candidate)
        self.assertIn("firewall_boundary:vultr_firewall_rule.operator_ssh", findings)
        self.assertIn("operator_source", findings)

    def test_vm_shape_region_and_vpc_attachment_are_rejected(self) -> None:
        candidate = copy.deepcopy(valid_plan())
        after = candidate["resource_changes"][3]["change"]["after"]
        after["plan"] = "vc2-16c-64gb"
        after["region"] = "ewr"
        after["vpc_ids"] = ["forbidden"]
        self.assertIn(
            "instance_boundary:vultr_instance.primary", plan.validate_plan(candidate)
        )

    def test_recovery_source_must_resolve_or_remain_computed(self) -> None:
        candidate = copy.deepcopy(valid_plan())
        candidate["resource_changes"][2]["change"]["after_unknown"] = {}
        self.assertIn("recovery_source", plan.validate_plan(candidate))

    def test_non_create_action_is_rejected(self) -> None:
        candidate = copy.deepcopy(valid_plan())
        candidate["resource_changes"][0]["change"]["actions"] = ["update"]
        self.assertIn(
            "resource_action:vultr_firewall_group.validation",
            plan.validate_plan(candidate),
        )


if __name__ == "__main__":
    unittest.main()
