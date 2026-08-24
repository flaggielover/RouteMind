from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from hashlib import sha256
from pathlib import Path
from typing import cast

import pytest

from routemind_compute.application.execution import canonical_digest
from routemind_compute.application.safe_rads_experiment import (
    SafeRadsExperimentError,
    audit_safe_rads_support,
    load_safe_rads_experiment_plan,
)

ROOT = Path(__file__).resolve().parents[3]
PLAN = ROOT / "docs/research/r3/manifests/rads/r3-345-safe-rads-experiment-v1.json"
SUPPORT = (
    "violation_events",
    "feasibility_outcomes",
    "route_cost_observations",
    "lateness_observations",
    "calibration_records",
    "tightness_sensitivity_runs",
)


def _payload() -> dict[str, object]:
    parsed: object = json.loads(PLAN.read_text(encoding="utf-8"))
    if not isinstance(parsed, Mapping):
        raise AssertionError("fixture must be an object")
    return cast(dict[str, object], parsed)


def _mapping(value: object) -> dict[str, object]:
    return dict(cast(Mapping[str, object], value))


def _write(tmp_path: Path, payload: dict[str, object]) -> Path:
    value = dict(payload)
    value["plan_digest"] = canonical_digest({k: v for k, v in value.items() if k != "plan_digest"})
    path = tmp_path / "safe-rads-experiment.json"
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _support(**overrides: bool) -> dict[str, bool]:
    value = {field: False for field in SUPPORT}
    value.update(overrides)
    return value


def test_plan_and_lineage_are_frozen() -> None:
    plan = load_safe_rads_experiment_plan(PLAN)
    assert plan.experiment_id == "r3-345-safe-rads-v1"
    assert plan.plan_digest == "182a3e6217f2c8e918049a4d55b78e340c8882a58e5dad106a7f738c3433783c"
    assert plan.manifest_sha256 == sha256(PLAN.read_bytes()).hexdigest()


def test_audit_reports_no_safe_outcomes_without_logs() -> None:
    audit = audit_safe_rads_support(load_safe_rads_experiment_plan(PLAN), _support())
    assert audit.status == "INSUFFICIENT_DATA"
    assert audit.available_fields == ()
    assert audit.missing_fields == SUPPORT
    assert all(status == "NOT_REPORTED_NO_SAFE_OUTCOMES" for _, status in audit.metric_status)


def test_audit_reports_ready_only_for_complete_support() -> None:
    audit = audit_safe_rads_support(
        load_safe_rads_experiment_plan(PLAN), {field: True for field in SUPPORT}
    )
    assert audit.status == "READY_FOR_EXECUTION"
    assert audit.available_fields == SUPPORT
    assert audit.missing_fields == ()


def test_loader_rejects_json_digest_and_shape(tmp_path: Path) -> None:
    invalid = tmp_path / "invalid.json"
    invalid.write_bytes(b"bad")
    with pytest.raises(SafeRadsExperimentError, match="UTF-8 JSON"):
        load_safe_rads_experiment_plan(invalid)
    scalar = tmp_path / "scalar.json"
    scalar.write_text("[]", encoding="utf-8")
    with pytest.raises(SafeRadsExperimentError, match="JSON object"):
        load_safe_rads_experiment_plan(scalar)
    payload = _payload()
    payload["question"] = "tampered"
    forged = tmp_path / "forged.json"
    forged.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(SafeRadsExperimentError, match="digest"):
        load_safe_rads_experiment_plan(forged)
    payload = _payload()
    payload["comparison_arms"] = ["fixed"]
    with pytest.raises(SafeRadsExperimentError, match="arms"):
        load_safe_rads_experiment_plan(_write(tmp_path, payload))


def test_loader_rejects_policy_threshold_lineage_and_support_drift(tmp_path: Path) -> None:
    def reject(mutate: Callable[[dict[str, object]], None], match: str) -> None:
        payload = _payload()
        mutate(payload)
        with pytest.raises(SafeRadsExperimentError, match=match):
            load_safe_rads_experiment_plan(_write(tmp_path, payload))

    reject(lambda p: p.update(task_id="R3-344"), "identity")
    reject(lambda p: p.update(safe_rads_reference="other"), "references")
    reject(lambda p: p.update(required_metrics=["risk"]), "metrics")
    reject(
        lambda p: p.update(thresholds={**_mapping(p["thresholds"]), "minimum_observations": 10}),
        "thresholds",
    )
    reject(
        lambda p: p.update(
            support_requirements={
                **_mapping(p["support_requirements"]),
                "synthetic_replay": True,
            }
        ),
        "read-only",
    )
    reject(
        lambda p: p.update(
            artifact_lineage={**_mapping(p["artifact_lineage"]), "pilot_plan": "0" * 64}
        ),
        "lineage",
    )
    reject(
        lambda p: p.update(
            execution_policy={
                **_mapping(p["execution_policy"]),
                "r3_325_rerun": True,
            }
        ),
        "read-only",
    )


def test_loader_rejects_nested_types_and_support_shape(tmp_path: Path) -> None:
    payload = _payload()
    payload["thresholds"] = "invalid"
    with pytest.raises(SafeRadsExperimentError, match="object"):
        load_safe_rads_experiment_plan(_write(tmp_path, payload))
    payload = _payload()
    payload["support_requirements"] = {
        **_mapping(payload["support_requirements"]),
        "required_fields": ["switch_events"],
    }
    with pytest.raises(SafeRadsExperimentError, match="support fields"):
        load_safe_rads_experiment_plan(_write(tmp_path, payload))
    plan = load_safe_rads_experiment_plan(PLAN)
    with pytest.raises(SafeRadsExperimentError, match="support fields"):
        audit_safe_rads_support(plan, {"violation_events": False})
