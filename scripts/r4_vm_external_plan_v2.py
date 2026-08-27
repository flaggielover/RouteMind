from __future__ import annotations

import argparse
import json
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import Any

EXPECTED_TYPES = Counter(
    {"vultr_firewall_group": 1, "vultr_firewall_rule": 2, "vultr_instance": 2}
)
EXPECTED_ADDRESSES = {
    "vultr_firewall_group.validation",
    "vultr_firewall_rule.operator_ssh",
    "vultr_firewall_rule.recovery_to_primary_ssh",
    "vultr_instance.primary",
    "vultr_instance.recovery",
}
EXPECTED_PLANS = {
    "vultr_instance.primary": "vc2-8c-32gb",
    "vultr_instance.recovery": "vc2-2c-4gb",
}


class VmExternalPlanV2Error(ValueError):
    pass


def load_plan(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise VmExternalPlanV2Error(f"cannot load Terraform plan: {path}") from exc
    if not isinstance(value, dict):
        raise VmExternalPlanV2Error("Terraform plan root must be an object")
    return value


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def validate_plan(plan: Mapping[str, Any], *, destroy: bool = False) -> tuple[str, ...]:
    findings: list[str] = []
    changes = plan.get("resource_changes")
    if not isinstance(changes, list):
        return ("resource_changes",)
    expected_action = ["delete"] if destroy else ["create"]
    actual_types: Counter[str] = Counter()
    actual_addresses: set[str] = set()
    for item in changes:
        if not isinstance(item, Mapping):
            findings.append("resource_change")
            continue
        address = str(item.get("address"))
        resource_type = str(item.get("type"))
        change = _mapping(item.get("change"))
        actions = change.get("actions")
        actual_addresses.add(address)
        actual_types[resource_type] += 1
        if actions != expected_action:
            findings.append(f"resource_action:{address}")
        if resource_type not in EXPECTED_TYPES:
            findings.append(f"resource_type:{resource_type}")
        if destroy:
            continue
        after = _mapping(change.get("after"))
        after_unknown = _mapping(change.get("after_unknown"))
        if resource_type == "vultr_instance":
            if (
                after.get("plan") != EXPECTED_PLANS.get(address)
                or after.get("region") != "nrt"
                or after.get("backups") != "disabled"
                or after.get("enable_ipv6") is not False
                or after.get("ddos_protection") is not False
                or after.get("activation_email") is not False
                or after.get("vpc_ids") not in (None, [])
            ):
                findings.append(f"instance_boundary:{address}")
        if resource_type == "vultr_firewall_rule":
            if (
                after.get("protocol") != "tcp"
                or after.get("ip_type") != "v4"
                or str(after.get("port")) != "22"
                or after.get("subnet_size") != 32
            ):
                findings.append(f"firewall_boundary:{address}")
            if address == "vultr_firewall_rule.operator_ssh" and after.get("subnet") in {
                "0.0.0.0",
                "::",
            }:
                findings.append("operator_source")
            if address == "vultr_firewall_rule.recovery_to_primary_ssh" and not (
                after_unknown.get("subnet") is True or bool(after.get("subnet"))
            ):
                findings.append("recovery_source")
    if actual_types != EXPECTED_TYPES:
        findings.append("resource_inventory")
    if actual_addresses != EXPECTED_ADDRESSES:
        findings.append("resource_addresses")
    return tuple(sorted(set(findings)))


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the exact no-new-VPC VM v2 plan")
    parser.add_argument("plan", type=Path)
    parser.add_argument("--destroy", action="store_true")
    args = parser.parse_args()
    findings = validate_plan(load_plan(args.plan), destroy=args.destroy)
    if findings:
        print("FAIL: " + ", ".join(findings))
        return 1
    print("PASS: exact no-new-VPC VM v2 Terraform plan")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
