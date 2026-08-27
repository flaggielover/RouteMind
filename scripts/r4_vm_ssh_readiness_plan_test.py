from __future__ import annotations

import copy
import unittest

from r4_vm_ssh_readiness_plan import validate_plan


def change(address: str, resource_type: str, after: dict[str, object]) -> dict[str, object]:
    return {
        "address": address,
        "type": resource_type,
        "change": {"actions": ["create"], "after": after},
    }


def valid_plan() -> dict[str, object]:
    return {
        "resource_changes": [
            change("vultr_firewall_group.diagnostic", "vultr_firewall_group", {}),
            change(
                "vultr_firewall_rule.operator_ssh",
                "vultr_firewall_rule",
                {
                    "protocol": "tcp",
                    "ip_type": "v4",
                    "port": "22",
                    "subnet": "203.0.113.9",
                    "subnet_size": 32,
                },
            ),
            change(
                "vultr_instance.diagnostic",
                "vultr_instance",
                {
                    "plan": "vc2-1c-1gb",
                    "region": "nrt",
                    "os_id": 2284,
                    "user_scheme": "root",
                    "backups": "disabled",
                    "enable_ipv6": False,
                    "ddos_protection": False,
                    "activation_email": False,
                    "vpc_ids": [],
                },
            ),
        ]
    }


class SshReadinessPlanTest(unittest.TestCase):
    def test_exact_plan_passes(self) -> None:
        self.assertEqual((), validate_plan(valid_plan()))

    def test_wider_firewall_fails(self) -> None:
        plan = valid_plan()
        plan["resource_changes"][1]["change"]["after"]["subnet"] = "0.0.0.0"
        plan["resource_changes"][1]["change"]["after"]["subnet_size"] = 0
        self.assertIn("firewall_boundary", validate_plan(plan))

    def test_larger_plan_fails(self) -> None:
        plan = valid_plan()
        plan["resource_changes"][2]["change"]["after"]["plan"] = "vc2-2c-4gb"
        self.assertIn("instance_boundary", validate_plan(plan))

    def test_extra_resource_fails(self) -> None:
        plan = valid_plan()
        plan["resource_changes"].append(
            change("vultr_vpc.unapproved", "vultr_vpc", {"region": "nrt"})
        )
        findings = validate_plan(plan)
        self.assertIn("resource_inventory", findings)
        self.assertIn("resource_type:vultr_vpc", findings)

    def test_destroy_requires_only_delete_actions(self) -> None:
        plan = valid_plan()
        destroy_plan = copy.deepcopy(plan)
        for item in destroy_plan["resource_changes"]:
            item["change"]["actions"] = ["delete"]
        self.assertEqual((), validate_plan(destroy_plan, destroy=True))


if __name__ == "__main__":
    unittest.main(verbosity=2)
