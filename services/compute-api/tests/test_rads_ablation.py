from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from hashlib import sha256
from pathlib import Path
from typing import cast

import pytest

from routemind_compute.application.execution import canonical_digest
from routemind_compute.application.rads_ablation import (
    RadsAblationError,
    audit_rads_ablation_support,
    load_rads_ablation_plan,
)

ROOT = Path(__file__).resolve().parents[3]
PLAN = ROOT / "docs/research/r3/manifests/rads/r3-348-rads-ablation-v1.json"
SUPPORT = (
    "common_stream_identity",
    "decision_outcomes",
    "switching_observations",
    "constraint_outcomes",
    "uncertainty_calibration",
    "threshold_sensitivity_runs",
)


def _payload() -> dict[str, object]:
    value: object = json.loads(PLAN.read_text(encoding="utf-8"))
    return dict(cast(Mapping[str, object], value))


def _mapping(value: object) -> dict[str, object]:
    return dict(cast(Mapping[str, object], value))


def _write(tmp_path: Path, payload: dict[str, object]) -> Path:
    value = dict(payload)
    value["plan_digest"] = canonical_digest({k: v for k, v in value.items() if k != "plan_digest"})
    path = tmp_path / "rads-ablation.json"
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    return path


def test_plan_freezes_all_dimensions_and_lineage() -> None:
    plan = load_rads_ablation_plan(PLAN)
    assert plan.experiment_id == "r3-348-rads-ablation-v1"
    assert plan.manifest_sha256 == sha256(PLAN.read_bytes()).hexdigest()
    rows = cast(list[dict[str, object]], plan.payload["ablations"])
    assert tuple(row["dimension"] for row in rows) == (
        "risk",
        "adaptation",
        "hysteresis",
        "uncertainty",
        "counterfactual_feature",
        "threshold",
    )


def test_audit_is_insufficient_without_component_logs() -> None:
    audit = audit_rads_ablation_support(
        load_rads_ablation_plan(PLAN), {field: False for field in SUPPORT}
    )
    assert audit.status == "INSUFFICIENT_DATA"
    assert audit.missing_fields == SUPPORT
    assert dict(audit.dimension_status)["counterfactual_feature"] == (
        "NOT_APPLICABLE_FEATURE_ABSENT"
    )
    assert dict(audit.dimension_status)["risk"] == "NOT_EVALUATED_NO_ABLATION_LOGS"
    assert all(status == "NOT_REPORTED_NO_ABLATION_LOGS" for _, status in audit.metric_status)


def test_audit_is_ready_only_with_complete_support() -> None:
    audit = audit_rads_ablation_support(
        load_rads_ablation_plan(PLAN), {field: True for field in SUPPORT}
    )
    assert audit.status == "READY_FOR_EXECUTION"
    assert audit.available_fields == SUPPORT
    assert audit.missing_fields == ()
    assert dict(audit.dimension_status)["counterfactual_feature"].startswith("NOT_APPLICABLE")


def test_loader_rejects_invalid_json_digest_and_shape(tmp_path: Path) -> None:
    invalid = tmp_path / "invalid.json"
    invalid.write_bytes(b"bad")
    with pytest.raises(RadsAblationError, match="UTF-8 JSON"):
        load_rads_ablation_plan(invalid)
    scalar = tmp_path / "scalar.json"
    scalar.write_text("[]", encoding="utf-8")
    with pytest.raises(RadsAblationError, match="JSON object"):
        load_rads_ablation_plan(scalar)
    payload = _payload()
    payload["question"] = "tampered"
    forged = tmp_path / "forged.json"
    forged.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(RadsAblationError, match="digest"):
        load_rads_ablation_plan(forged)


def test_loader_rejects_dimension_analysis_and_support_drift(tmp_path: Path) -> None:
    def reject(mutate: Callable[[dict[str, object]], None], match: str) -> None:
        payload = _payload()
        mutate(payload)
        with pytest.raises(RadsAblationError, match=match):
            load_rads_ablation_plan(_write(tmp_path, payload))

    reject(lambda p: p.update(task_id="R3-349"), "identity")
    reject(lambda p: p.update(ablations=[]), "dimensions")
    reject(
        lambda p: p.update(analysis_plan={**_mapping(p["analysis_plan"]), "minimum_pairs": 1}),
        "analysis plan",
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


def test_loader_rejects_lineage_policy_and_support_shape(tmp_path: Path) -> None:
    payload = _payload()
    payload["source_lineage"] = {
        **_mapping(payload["source_lineage"]),
        "pilot_ledger": "0" * 64,
    }
    with pytest.raises(RadsAblationError, match="lineage"):
        load_rads_ablation_plan(_write(tmp_path, payload))
    payload = _payload()
    payload["execution_policy"] = {
        **_mapping(payload["execution_policy"]),
        "post_result_removals": "CONFIRMATORY",
    }
    with pytest.raises(RadsAblationError, match="exploratory boundary"):
        load_rads_ablation_plan(_write(tmp_path, payload))
    with pytest.raises(RadsAblationError, match="support fields"):
        audit_rads_ablation_support(load_rads_ablation_plan(PLAN), {"decision_outcomes": False})
