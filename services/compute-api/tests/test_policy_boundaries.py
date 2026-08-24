from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from hashlib import sha256
from pathlib import Path
from typing import cast

import pytest

from routemind_compute.application.execution import canonical_digest
from routemind_compute.application.policy_boundaries import (
    PolicyBoundaryError,
    audit_policy_boundary_support,
    load_policy_boundary_plan,
)

ROOT = Path(__file__).resolve().parents[3]
PLAN = ROOT / "docs/research/r3/manifests/rads/r3-346-policy-boundaries-v1.json"
SUPPORT = (
    "empirical_stability_cells",
    "selected_strategy_labels",
    "alternate_strategy_outcomes",
    "risk_outcomes",
    "feasibility_outcomes",
    "pairing_unit",
    "regime_identity",
)


def _payload() -> dict[str, object]:
    parsed: object = json.loads(PLAN.read_text(encoding="utf-8"))
    return dict(cast(Mapping[str, object], parsed))


def _mapping(value: object) -> dict[str, object]:
    return dict(cast(Mapping[str, object], value))


def _write(tmp_path: Path, payload: dict[str, object]) -> Path:
    value = dict(payload)
    value["plan_digest"] = canonical_digest({k: v for k, v in value.items() if k != "plan_digest"})
    path = tmp_path / "policy-boundaries.json"
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    return path


def test_plan_freezes_interpretable_method_support_and_lineage() -> None:
    plan = load_policy_boundary_plan(PLAN)
    assert plan.study_id == "r3-346-interpretable-policy-boundaries-v1"
    assert plan.manifest_sha256 == sha256(PLAN.read_bytes()).hexdigest()
    learning = cast(dict[str, object], plan.payload["learning_policy"])
    assert learning == {
        "model_family": "SHALLOW_AXIS_ALIGNED_RULE_TREE",
        "maximum_depth": 3,
        "selection_objective": "INTERPRETABILITY_WITH_EMPIRICAL_SUPPORT",
        "predictive_accuracy_only": False,
    }


def test_current_sources_refuse_unsupported_policy_boundaries() -> None:
    audit = audit_policy_boundary_support(
        load_policy_boundary_plan(PLAN),
        {field: False for field in SUPPORT},
        {},
        0,
    )
    assert audit.status == "INSUFFICIENT_DATA"
    assert audit.missing_fields == SUPPORT
    assert audit.strategy_counts == ()
    assert audit.eligible_stability_cells == 0
    assert all(
        status == "NOT_MAPPED_INSUFFICIENT_EMPIRICAL_SUPPORT" for _, status in audit.axis_status
    )
    assert all(
        status == "NOT_ESTIMATED_INSUFFICIENT_BOUNDARY_SUPPORT" for _, status in audit.output_status
    )
    assert audit.uncertainty_status == "NOT_ESTIMATED_NO_SUPPORTED_BOUNDARY"
    assert audit.sensitivity_status == "NOT_RUN_NO_SUPPORTED_BOUNDARY"


def test_complete_support_must_meet_class_and_stability_thresholds() -> None:
    plan = load_policy_boundary_plan(PLAN)
    support = {field: True for field in SUPPORT}
    underpowered = audit_policy_boundary_support(plan, support, {"rads_h": 29, "safe": 31}, 2)
    assert underpowered.status == "INSUFFICIENT_DATA"
    assert "30 records" in underpowered.reason
    too_few_cells = audit_policy_boundary_support(plan, support, {"rads_h": 30, "safe": 30}, 1)
    assert too_few_cells.status == "INSUFFICIENT_DATA"
    assert "fewer than two" in too_few_cells.reason
    ready = audit_policy_boundary_support(plan, support, {"rads_h": 30, "safe": 30}, 2)
    assert ready.status == "READY_FOR_INTERPRETABLE_LEARNING"
    assert all(status == "READY_FOR_SUPPORTED_BOUNDARY" for _, status in ready.axis_status)
    assert ready.uncertainty_status == "READY_FOR_PAIRED_BOOTSTRAP_INTERVALS"


def test_audit_rejects_support_and_count_shape() -> None:
    plan = load_policy_boundary_plan(PLAN)
    with pytest.raises(PolicyBoundaryError, match="support fields"):
        audit_policy_boundary_support(plan, {"risk_outcomes": False}, {}, 0)
    with pytest.raises(PolicyBoundaryError, match="strategy counts"):
        audit_policy_boundary_support(plan, {field: False for field in SUPPORT}, {"rads_h": -1}, 0)
    with pytest.raises(PolicyBoundaryError, match="stability cells"):
        audit_policy_boundary_support(plan, {field: False for field in SUPPORT}, {}, -1)


def test_loader_rejects_json_digest_and_shape(tmp_path: Path) -> None:
    invalid = tmp_path / "invalid.json"
    invalid.write_bytes(b"bad")
    with pytest.raises(PolicyBoundaryError, match="UTF-8 JSON"):
        load_policy_boundary_plan(invalid)
    scalar = tmp_path / "scalar.json"
    scalar.write_text("[]", encoding="utf-8")
    with pytest.raises(PolicyBoundaryError, match="JSON object"):
        load_policy_boundary_plan(scalar)
    payload = _payload()
    payload["question"] = "tampered"
    forged = tmp_path / "forged.json"
    forged.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(PolicyBoundaryError, match="digest"):
        load_policy_boundary_plan(forged)


def test_loader_rejects_method_coverage_lineage_and_execution_drift(tmp_path: Path) -> None:
    def reject(mutate: Callable[[dict[str, object]], None], match: str) -> None:
        payload = _payload()
        mutate(payload)
        with pytest.raises(PolicyBoundaryError, match=match):
            load_policy_boundary_plan(_write(tmp_path, payload))

    reject(lambda p: p.update(task_id="R3-345"), "identity")
    reject(lambda p: p.update(boundary_axes=[]), "axes")
    reject(
        lambda p: p.update(
            learning_policy={**_mapping(p["learning_policy"]), "predictive_accuracy_only": True}
        ),
        "learning policy",
    )
    reject(
        lambda p: p.update(
            coverage_policy={**_mapping(p["coverage_policy"]), "minimum_records_per_strategy": 2}
        ),
        "coverage policy",
    )
    reject(
        lambda p: p.update(
            source_lineage={**_mapping(p["source_lineage"]), "stability_map_plan": "0" * 64}
        ),
        "lineage",
    )
    reject(
        lambda p: p.update(
            execution_policy={**_mapping(p["execution_policy"]), "black_box_substitution": True}
        ),
        "read-only and interpretable",
    )


def test_loader_rejects_output_uncertainty_sensitivity_and_support_drift(
    tmp_path: Path,
) -> None:
    def reject(mutate: Callable[[dict[str, object]], None], match: str) -> None:
        payload = _payload()
        mutate(payload)
        with pytest.raises(PolicyBoundaryError, match=match):
            load_policy_boundary_plan(_write(tmp_path, payload))

    reject(lambda p: p.update(required_outputs=[]), "outputs")
    reject(
        lambda p: p.update(
            uncertainty_policy={**_mapping(p["uncertainty_policy"]), "confidence_level": 0.9}
        ),
        "uncertainty policy",
    )
    reject(
        lambda p: p.update(
            sensitivity_policy={
                **_mapping(p["sensitivity_policy"]),
                "required_for_boundary": False,
            }
        ),
        "sensitivity policy",
    )
    reject(
        lambda p: p.update(
            support_requirements={
                **_mapping(p["support_requirements"]),
                "synthetic_substitution": True,
            }
        ),
        "fail-closed",
    )
    reject(lambda p: p.update(claim_boundary="accuracy-is-enough"), "claim boundary")
    reject(lambda p: p.update(boundary_axes="invalid"), "array")
    reject(
        lambda p: p.update(
            execution_policy={
                **_mapping(p["execution_policy"]),
                "manifest_changes": "IN_PLACE",
            }
        ),
        "change policy",
    )
