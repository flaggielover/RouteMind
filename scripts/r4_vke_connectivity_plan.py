from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

EXPECTED_CREATE_TYPES = Counter(
    {
        "vultr_firewall_group": 1,
        "vultr_firewall_rule": 3,
        "vultr_instance": 1,
        "vultr_kubernetes": 1,
    }
)
EXPECTED_ADDRESSES = {
    "vultr_firewall_group.recovery",
    "vultr_firewall_rule.recovery_ssh",
    "vultr_firewall_rule.vke_api_operator",
    "vultr_firewall_rule.vke_api_recovery",
    "vultr_instance.recovery",
    "vultr_kubernetes.diagnostic",
}


class DiagnosticPlanError(ValueError):
    pass


def load_plan(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DiagnosticPlanError(f"cannot load Terraform plan: {path}") from exc
    if not isinstance(value, dict):
        raise DiagnosticPlanError("Terraform plan root must be an object")
    return value


def validate_plan(plan: dict[str, Any], *, destroy: bool = False) -> tuple[str, ...]:
    findings: list[str] = []
    changes = plan.get("resource_changes")
    if not isinstance(changes, list):
        return ("resource_changes",)
    expected_action = ["delete"] if destroy else ["create"]
    actual_types: Counter[str] = Counter()
    actual_addresses: set[str] = set()
    for change in changes:
        if not isinstance(change, dict):
            findings.append("resource_change")
            continue
        address = change.get("address")
        resource_type = change.get("type")
        actions = change.get("change", {}).get("actions", [])
        actual_addresses.add(str(address))
        actual_types[str(resource_type)] += 1
        if actions != expected_action:
            findings.append(f"resource_action:{address}")
        if resource_type not in EXPECTED_CREATE_TYPES:
            findings.append(f"resource_type:{resource_type}")
    if actual_types != EXPECTED_CREATE_TYPES:
        findings.append("resource_inventory")
    if actual_addresses != EXPECTED_ADDRESSES:
        findings.append("resource_addresses")
    return tuple(sorted(set(findings)))


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the exact VKE diagnostic Terraform plan")
    parser.add_argument("plan", type=Path)
    parser.add_argument("--destroy", action="store_true")
    args = parser.parse_args()
    findings = validate_plan(load_plan(args.plan), destroy=args.destroy)
    if findings:
        print("FAIL: " + ", ".join(findings))
        return 1
    print("PASS: exact VKE diagnostic Terraform plan")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
