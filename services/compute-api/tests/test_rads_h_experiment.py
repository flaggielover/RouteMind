from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from hashlib import sha256
from pathlib import Path
from typing import cast

import pytest

from routemind_compute.application.execution import canonical_digest
from routemind_compute.application.rads_h_experiment import (
    RadsHExperimentError,
    audit_rads_h_support,
    load_rads_h_experiment_plan,
)

ROOT = Path(__file__).resolve().parents[3]
PLAN = ROOT / "docs" / "research" / "r3" / "manifests" / "rads" / "r3-342-rads-h-experiment-v1.json"
SUPPORT_FIELDS = (
    "tick_level_strategy_sequence",
    "switch_events",
    "dwell_observations",
    "service_outcomes",
    "latency_observations",
    "recovery_windows",
)


def _payload() -> dict[str, object]:
    parsed: object = json.loads(PLAN.read_text(encoding="utf-8"))
    if not isinstance(parsed, Mapping):
        raise AssertionError("fixture must be an object")
    return cast(dict[str, object], parsed)


def _mapping(value: object) -> dict[str, object]:
    return dict(cast(Mapping[str, object], value))


def _write(tmp_path: Path, payload: dict[str, object]) -> Path:
    unsigned = dict(payload)
    unsigned["plan_digest"] = canonical_digest(
        {key: value for key, value in unsigned.items() if key != "plan_digest"}
    )
    path = tmp_path / "rads-h-experiment.json"
    path.write_text(json.dumps(unsigned, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _support(**overrides: bool) -> dict[str, bool]:
    result = {field: False for field in SUPPORT_FIELDS}
    result.update(overrides)
    return result


def test_plan_freezes_arms_thresholds_lineage_and_digest() -> None:
    plan = load_rads_h_experiment_plan(PLAN)
    assert plan.experiment_id == "r3-342-rads-h-v1"
    assert plan.plan_digest == ("725bce8111db8652c6b52ef1c71e63429594aa4a329e0372e524471ea41ac967")
    assert plan.manifest_sha256 == sha256(PLAN.read_bytes()).hexdigest()
    assert plan.payload["comparison_arms"] == [
        "no_hysteresis",
        "fixed",
        "rads_baseline",
        "cooldown",
        "rads_h",
    ]


def test_support_audit_is_fail_closed_without_tick_logs() -> None:
    plan = load_rads_h_experiment_plan(PLAN)
    audit = audit_rads_h_support(plan, _support())
    assert audit.status == "INSUFFICIENT_DATA"
    assert audit.available_fields == ()
    assert audit.missing_fields == SUPPORT_FIELDS
    assert all(status == "NOT_REPORTED_NO_SWITCH_LOGS" for _, status in audit.metric_status)
    assert "no required tick-level switching observations" in audit.reason


def test_support_audit_reports_ready_only_when_every_field_is_present() -> None:
    plan = load_rads_h_experiment_plan(PLAN)
    audit = audit_rads_h_support(plan, {field: True for field in SUPPORT_FIELDS})
    assert audit.status == "READY_FOR_EXECUTION"
    assert audit.available_fields == SUPPORT_FIELDS
    assert audit.missing_fields == ()
    assert all(status == "READY_FOR_EXECUTION" for _, status in audit.metric_status)


def test_support_audit_rejects_shape_drift() -> None:
    plan = load_rads_h_experiment_plan(PLAN)
    with pytest.raises(RadsHExperimentError, match="support fields mismatch"):
        audit_rads_h_support(plan, {"switch_events": False})


def test_loader_rejects_invalid_json_scalar_and_digest(tmp_path: Path) -> None:
    invalid = tmp_path / "invalid.json"
    invalid.write_bytes(b"not-json")
    with pytest.raises(RadsHExperimentError, match="UTF-8 JSON"):
        load_rads_h_experiment_plan(invalid)
    scalar = tmp_path / "scalar.json"
    scalar.write_text("[]", encoding="utf-8")
    with pytest.raises(RadsHExperimentError, match="JSON object"):
        load_rads_h_experiment_plan(scalar)
    payload = _payload()
    payload["question"] = "tampered"
    forged = tmp_path / "forged.json"
    forged.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(RadsHExperimentError, match="digest"):
        load_rads_h_experiment_plan(forged)


def test_loader_rejects_identity_arms_metrics_and_threshold_drift(tmp_path: Path) -> None:
    def reject(mutate: Callable[[dict[str, object]], None], match: str) -> None:
        payload = _payload()
        mutate(payload)
        with pytest.raises(RadsHExperimentError, match=match):
            load_rads_h_experiment_plan(_write(tmp_path, payload))

    reject(lambda p: p.update(task_id="R3-341"), "identity")
    reject(lambda p: p.update(experiment_id="other"), "identifier")
    reject(lambda p: p.update(claim_boundary="other"), "claim boundary")
    reject(lambda p: p.update(comparison_arms=["fixed"]), "comparison arms")
    reject(lambda p: p.update(required_metrics=["switching_rate"]), "required metrics")
    reject(
        lambda p: p.update(thresholds={**_mapping(p["thresholds"]), "holm_family_size": 8}),
        "statistical thresholds",
    )


def test_loader_rejects_support_lineage_and_execution_drift(tmp_path: Path) -> None:
    def reject(mutate: Callable[[dict[str, object]], None], match: str) -> None:
        payload = _payload()
        mutate(payload)
        with pytest.raises(RadsHExperimentError, match=match):
            load_rads_h_experiment_plan(_write(tmp_path, payload))

    reject(
        lambda p: p.update(
            support_requirements={
                **_mapping(p["support_requirements"]),
                "synthetic_replay": True,
            }
        ),
        "synthetic replay",
    )
    reject(
        lambda p: p.update(
            artifact_lineage={
                **_mapping(p["artifact_lineage"]),
                "pilot_plan": "0" * 64,
            }
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
    reject(
        lambda p: p.update(
            support_requirements={
                **_mapping(p["support_requirements"]),
                "required_fields": ["switch_events"],
            }
        ),
        "support fields",
    )
    reject(
        lambda p: p.update(
            thresholds={
                **_mapping(p["thresholds"]),
                "switch_reduction_target": "nan",
            }
        ),
        "finite number",
    )


def test_loader_rejects_nested_types_and_extra_fields(tmp_path: Path) -> None:
    payload = _payload()
    payload["thresholds"] = "invalid"
    with pytest.raises(RadsHExperimentError, match="object"):
        load_rads_h_experiment_plan(_write(tmp_path, payload))
    payload = _payload()
    payload["artifact_lineage"] = {
        **_mapping(payload["artifact_lineage"]),
        "extra": "x",
    }
    with pytest.raises(RadsHExperimentError, match="lineage fields"):
        load_rads_h_experiment_plan(_write(tmp_path, payload))
    payload = _payload()
    payload["unexpected"] = True
    with pytest.raises(RadsHExperimentError, match="fields mismatch"):
        load_rads_h_experiment_plan(_write(tmp_path, payload))
