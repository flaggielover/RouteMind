from __future__ import annotations

import argparse
import json
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import Any

EXPECTED_TYPES = Counter(
    {"vultr_firewall_group": 1, "vultr_firewall_rule": 1, "vultr_instance": 1}
)
EXPECTED_ADDRESSES = {
    "vultr_firewall_group.diagnostic",
    "vultr_firewall_rule.operator_ssh",
    "vultr_instance.diagnostic",
}


class SshReadinessPlanError(ValueError):
    pass


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def load_plan(path: Path) -> dict[str, Any]:
    try:
        result = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SshReadinessPlanError(f"cannot load Terraform plan: {path}") from exc
    if not isinstance(result, dict):
        raise SshReadinessPlanError("Terraform plan root must be an object")
    return result


def validate_plan(
    plan: Mapping[str, Any], *, destroy: bool = False, allow_partial_destroy: bool = False
) -> tuple[str, ...]:
    findings: list[str] = []
    changes = plan.get("resource_changes")
    if changes is None and destroy and allow_partial_destroy:
        return ()
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
        after = _mapping(change.get("after"))
        actual_addresses.add(address)
        actual_types[resource_type] += 1
        if change.get("actions") != expected_action:
            findings.append(f"resource_action:{address}")
        if resource_type not in EXPECTED_TYPES:
            findings.append(f"resource_type:{resource_type}")
        if destroy:
            continue
        if resource_type == "vultr_instance" and (
            after.get("plan") != "vc2-1c-1gb"
            or after.get("region") != "nrt"
            or after.get("os_id") != 2284
            or after.get("user_scheme") != "root"
            or after.get("backups") != "disabled"
            or after.get("enable_ipv6") is not False
            or after.get("ddos_protection") is not False
            or after.get("activation_email") is not False
            or after.get("vpc_ids") not in (None, [])
        ):
            findings.append("instance_boundary")
        if resource_type == "vultr_firewall_rule" and (
            after.get("protocol") != "tcp"
            or after.get("ip_type") != "v4"
            or str(after.get("port")) != "22"
            or after.get("subnet_size") != 32
            or after.get("subnet") in {"0.0.0.0", "::", "0.0.0.0/0", "::/0"}
        ):
            findings.append("firewall_boundary")
    if destroy and allow_partial_destroy:
        if any(actual_types[key] > count for key, count in EXPECTED_TYPES.items()):
            findings.append("resource_inventory")
        if any(key not in EXPECTED_TYPES for key in actual_types):
            findings.append("resource_inventory")
        if not actual_addresses.issubset(EXPECTED_ADDRESSES):
            findings.append("resource_addresses")
    else:
        if actual_types != EXPECTED_TYPES:
            findings.append("resource_inventory")
        if actual_addresses != EXPECTED_ADDRESSES:
            findings.append("resource_addresses")
    return tuple(sorted(set(findings)))


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the exact SSH-readiness plan")
    parser.add_argument("plan", type=Path)
    parser.add_argument("--destroy", action="store_true")
    parser.add_argument("--allow-partial-destroy", action="store_true")
    arguments = parser.parse_args()
    if arguments.allow_partial_destroy and not arguments.destroy:
        parser.error("--allow-partial-destroy requires --destroy")
    findings = validate_plan(
        load_plan(arguments.plan),
        destroy=arguments.destroy,
        allow_partial_destroy=arguments.allow_partial_destroy,
    )
    if findings:
        print("FAIL: " + ", ".join(findings))
        return 1
    print("PASS: exact Tokyo VM SSH-readiness Terraform plan")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
